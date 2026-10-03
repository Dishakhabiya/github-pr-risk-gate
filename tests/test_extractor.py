import pytest
from app.features.extractor import extract_features


def test_normal_pr():
    pr_data = {
        "pr_id": 101,
        "repository": "owner/repo",
        "commits": [{"sha": "abc"}, {"sha": "def"}],
        "changed_files": [
            {"filename": "app/main.py", "status": "modified"},
            {"filename": "tests/test_main.py", "status": "added"},
            {"filename": "README.md", "status": "modified"},
        ],
    }
    diff_data = {
        "files_changed": ["app/main.py", "tests/test_main.py", "README.md"],
        "num_added_lines": 80,
        "num_deleted_lines": 20,
        "binary_files": [],
    }

    features = extract_features(pr_data, diff_data)

    assert features["files_changed"] == 3
    assert features["lines_added"] == 80
    assert features["lines_deleted"] == 20
    assert features["total_lines_changed"] == 100
    assert features["commits_count"] == 2
    assert features["additions_to_deletions_ratio"] == 4.0
    assert features["average_changes_per_file"] == round(100 / 3, 4)
    assert features["source_files_changed"] == 1
    assert features["test_files_changed"] == 1
    assert features["documentation_files_changed"] == 1
    assert features["config_files_changed"] == 0
    assert features["added_files"] == 1


def test_no_changed_files():
    pr_data = {"pr_id": 102, "commits": [], "changed_files": []}
    diff_data = {"files_changed": [], "num_added_lines": 0, "num_deleted_lines": 0}

    features = extract_features(pr_data, diff_data)

    assert features["files_changed"] == 0
    assert features["lines_added"] == 0
    assert features["lines_deleted"] == 0
    assert features["total_lines_changed"] == 0
    assert features["commits_count"] == 0
    assert features["additions_to_deletions_ratio"] == 0.0
    assert features["average_changes_per_file"] == 0.0


def test_no_commits():
    pr_data = {"pr_id": 103, "commits": [], "changed_files": [{"filename": "src/app.py", "status": "modified"}]}
    diff_data = {"files_changed": ["src/app.py"], "num_added_lines": 10, "num_deleted_lines": 2}

    features = extract_features(pr_data, diff_data)

    assert features["commits_count"] == 0
    assert features["files_changed"] == 1


def test_source_files():
    pr_data = {
        "changed_files": [
            {"filename": "src/api.py", "status": "modified"},
            {"filename": "src/utils.js", "status": "modified"},
            {"filename": "lib/core.cpp", "status": "added"},
        ]
    }
    diff_data = {
        "files_changed": ["src/api.py", "src/utils.js", "lib/core.cpp"],
        "num_added_lines": 30,
        "num_deleted_lines": 5,
    }

    features = extract_features(pr_data, diff_data)

    assert features["source_files_changed"] == 3
    assert features["test_files_changed"] == 0
    assert features["documentation_files_changed"] == 0
    assert features["config_files_changed"] == 0


def test_test_files():
    pr_data = {
        "changed_files": [
            {"filename": "tests/test_api.py", "status": "modified"},
            {"filename": "src/service.spec.ts", "status": "added"},
            {"filename": "backend/user_test.go", "status": "modified"},
        ]
    }
    diff_data = {
        "files_changed": ["tests/test_api.py", "src/service.spec.ts", "backend/user_test.go"],
        "num_added_lines": 40,
        "num_deleted_lines": 10,
    }

    features = extract_features(pr_data, diff_data)

    assert features["test_files_changed"] == 3
    assert features["source_files_changed"] == 0


def test_documentation_files():
    pr_data = {
        "changed_files": [
            {"filename": "README.md", "status": "modified"},
            {"filename": "docs/architecture.rst", "status": "added"},
            {"filename": "LICENSE", "status": "modified"},
        ]
    }
    diff_data = {
        "files_changed": ["README.md", "docs/architecture.rst", "LICENSE"],
        "num_added_lines": 15,
        "num_deleted_lines": 2,
    }

    features = extract_features(pr_data, diff_data)

    assert features["documentation_files_changed"] == 3
    assert features["source_files_changed"] == 0


def test_configuration_files():
    pr_data = {
        "changed_files": [
            {"filename": "requirements.txt", "status": "modified"},
            {"filename": "Dockerfile", "status": "modified"},
            {"filename": "config/settings.yaml", "status": "added"},
        ]
    }
    diff_data = {
        "files_changed": ["requirements.txt", "Dockerfile", "config/settings.yaml"],
        "num_added_lines": 12,
        "num_deleted_lines": 4,
    }

    features = extract_features(pr_data, diff_data)

    assert features["config_files_changed"] == 3
    assert features["source_files_changed"] == 0


def test_additions_deletions_calculation():
    # Case 1: normal ratio
    pr_data = {"changed_files": []}
    diff_data_1 = {"files_changed": ["f1.py"], "num_added_lines": 80, "num_deleted_lines": 20}
    feat_1 = extract_features(pr_data, diff_data_1)
    assert feat_1["lines_added"] == 80
    assert feat_1["lines_deleted"] == 20
    assert feat_1["total_lines_changed"] == 100
    assert feat_1["additions_to_deletions_ratio"] == 4.0

    # Case 2: zero deletions
    diff_data_2 = {"files_changed": ["f1.py"], "num_added_lines": 50, "num_deleted_lines": 0}
    feat_2 = extract_features(pr_data, diff_data_2)
    assert feat_2["additions_to_deletions_ratio"] == 50.0

    # Case 3: zero additions & zero deletions
    diff_data_3 = {"files_changed": [], "num_added_lines": 0, "num_deleted_lines": 0}
    feat_3 = extract_features(pr_data, diff_data_3)
    assert feat_3["additions_to_deletions_ratio"] == 0.0


def test_file_type_counting():
    pr_data = {
        "changed_files": [
            {"filename": "app/main.py", "status": "modified"},
            {"filename": "app/utils.py", "status": "modified"},
            {"filename": "docs/readme.md", "status": "modified"},
            {"filename": "config.json", "status": "modified"},
            {"filename": "Dockerfile", "status": "modified"},
        ]
    }
    diff_data = {
        "files_changed": ["app/main.py", "app/utils.py", "docs/readme.md", "config.json", "Dockerfile"],
        "num_added_lines": 50,
        "num_deleted_lines": 10,
    }

    features = extract_features(pr_data, diff_data)
    counts = features["file_type_counts"]

    assert counts["py"] == 2
    assert counts["md"] == 1
    assert counts["json"] == 1
    assert counts["no_extension"] == 1
