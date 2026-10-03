from unittest.mock import MagicMock, patch
import pytest

from app.dataset.collector import DatasetCollector, is_bot_author
from app.dataset.labeler import (
    assign_risk_labels,
    calculate_review_effort_score,
    check_has_linked_issue,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    METADATA_COLUMNS,
    OUTCOME_COLUMNS,
)


def test_review_effort_calculation():
    # 5 inline comments * 1.0 + 2 changes requested * 3.0 + 4 issue comments * 0.5 = 5 + 6 + 2 = 13.0
    score = calculate_review_effort_score(
        review_comments_count=5, changes_requested_count=2, issue_comments_count=4
    )
    assert score == 13.0


def test_percentile_threshold_calculation():
    # 10 records with scores 1 to 10
    records = [{"review_effort_score": float(i)} for i in range(1, 11)]
    labeled_records, threshold = assign_risk_labels(records, percentile_threshold=80.0)

    # 80th percentile of [1..10] is 8.2
    assert round(threshold, 1) == 8.2

    high_risk_records = [r for r in labeled_records if r[LABEL_COLUMN] == 1]
    low_risk_records = [r for r in labeled_records if r[LABEL_COLUMN] == 0]

    # Scores 9 and 10 are >= 8.2 -> HIGH RISK (1)
    assert len(high_risk_records) == 2
    assert len(low_risk_records) == 8
    assert all(r[LABEL_COLUMN] == 1 for r in high_risk_records if r["review_effort_score"] >= 9.0)


def test_bot_filtering():
    assert is_bot_author("dependabot[bot]") is True
    assert is_bot_author("renovate[bot]") is True
    assert is_bot_author("k8s-ci-robot") is True
    assert is_bot_author("tensorflow-jenkins") is True
    assert is_bot_author("octocat") is False
    assert is_bot_author("regular_developer") is False
    assert is_bot_author(None) is False


def test_has_linked_issue():
    assert check_has_linked_issue("Fixes #123 bug in parser", "Resolved issue") == 1
    assert check_has_linked_issue("Add new feature", "See #456 for context") == 1
    assert check_has_linked_issue("Simple refactor", "No issue referenced") == 0


def test_data_leakage_prevention_schema():
    """Verify strictly that no review/outcome or post-creation fields are in FEATURE_COLUMNS."""
    forbidden_outcome_fields = {
        "review_comments_count",
        "issue_comments_count",
        "changes_requested_count",
        "approved_count",
        "commented_count",
        "review_count",
        "review_effort_score",
        "risk_label",
        "merged",
        "closed_at",
        "merged_at",
        "turnaround_hours",
    }

    feature_set = set(FEATURE_COLUMNS)
    leakage = feature_set.intersection(forbidden_outcome_fields)

    assert len(leakage) == 0, f"Data leakage detected! Forbidden fields in FEATURE_COLUMNS: {leakage}"


def test_mocked_collector_process_single_pr(tmp_path):
    mock_client = MagicMock()

    # Mock PR summary from list endpoint
    pr_summary = {"number": 42, "user": {"login": "dev_user"}}

    # Mock fetch_pr_details (US-01)
    mock_pr_details = {
        "pr_id": 42,
        "repository": "owner/repo",
        "title": "Fix bug #10",
        "body": "Fixes #10 bug",
        "commits": [{"sha": "123"}],
        "changed_files": [
            {"filename": "app/main.py", "status": "modified", "additions": 10, "deletions": 2, "changes": 12}
        ],
        "diff": "diff --git a/app/main.py b/app/main.py\n--- a/app/main.py\n+++ b/app/main.py\n@@ -1,1 +1,1 @@\n-old\n+new",
    }

    # Mock full PR endpoint
    mock_full_pr = {
        "number": 42,
        "created_at": "2026-10-01T00:00:00Z",
        "review_comments": 4,
        "comments": 2,
        "merged": True,
    }

    # Mock reviews endpoint
    mock_reviews = [
        {"state": "CHANGES_REQUESTED"},
        {"state": "APPROVED"},
    ]

    mock_client.get_pull_request.return_value = mock_full_pr
    mock_client.get_pull_request_reviews.return_value = mock_reviews

    collector = DatasetCollector(client=mock_client, raw_dir=str(tmp_path))

    with patch("app.dataset.collector.fetch_pr_details", return_value=mock_pr_details):
        record = collector.process_single_pr("owner", "repo", pr_summary)

    assert record is not None
    assert record["repository"] == "owner/repo"
    assert record["pr_id"] == 42
    assert record["files_changed"] == 1
    assert record["lines_added"] == 1
    assert record["lines_deleted"] == 1
    assert record["review_comments_count"] == 4
    assert record["changes_requested_count"] == 1
    assert record["issue_comments_count"] == 2
    # Score = 4*1.0 + 1*3.0 + 2*0.5 = 8.0
    assert record["review_effort_score"] == 8.0
    assert record["merged"] is True
