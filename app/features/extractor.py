import os
from typing import Any, Dict, List


def _classify_file(filename: str) -> str:
    """Classify a file path into test, doc, config, or source category.

    Args:
        filename: Relative path or filename.

    Returns:
        One of 'test', 'doc', 'config', or 'source'.
    """
    lower_path = filename.lower()
    base_name = os.path.basename(lower_path)
    parts = lower_path.split("/")

    # 1. Exact config filenames take precedence over generic extensions (e.g. requirements.txt)
    config_filenames = {
        "dockerfile",
        "makefile",
        ".gitignore",
        ".dockerignore",
        ".env",
        ".env.example",
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "package.json",
        "cargo.toml",
        "go.mod",
        "go.sum",
    }
    if base_name in config_filenames:
        return "config"

    # 2. Test file identification
    is_test_dir = any(p in ("test", "tests", "spec", "specs", "__tests__", "testing") for p in parts[:-1])
    is_test_name = (
        base_name.startswith("test_")
        or base_name.startswith("spec_")
        or "_test." in base_name
        or ".test." in base_name
        or "_spec." in base_name
        or ".spec." in base_name
        or base_name.endswith("test")
        or base_name.endswith("spec")
    )
    if is_test_dir or is_test_name:
        return "test"

    # 3. Configuration / build files
    config_extensions = {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".env",
        ".xml",
        ".config",
        ".cfg",
        ".properties",
    }
    config_dirs = {"config", "configs", ".github", ".vscode", ".idea"}
    is_config_dir = any(p in config_dirs for p in parts[:-1])
    ext = os.path.splitext(base_name)[1]
    if is_config_dir or ext in config_extensions:
        return "config"

    # 4. Documentation files
    doc_extensions = {".md", ".markdown", ".rst", ".adoc", ".txt"}
    doc_names = {"readme", "changelog", "contributing", "license", "notice"}
    doc_dirs = {"doc", "docs", "documentation"}
    name_without_ext = os.path.splitext(base_name)[0]
    is_doc_dir = any(p in doc_dirs for p in parts[:-1])
    is_doc_file = ext in doc_extensions or name_without_ext in doc_names
    if is_doc_dir or is_doc_file:
        return "doc"

    # Default to source file
    return "source"


def extract_features(pr_data: Dict[str, Any], diff_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract deterministic numeric features from PR and diff data.

    Args:
        pr_data: Structured PR dictionary from US-01.
        diff_data: Preprocessed diff dictionary from US-02.

    Returns:
        Dict containing ML-friendly numeric features.
    """
    diff_files = diff_data.get("files_changed", [])
    pr_files_raw = pr_data.get("changed_files", [])

    file_paths: List[str] = list(
        dict.fromkeys(
            [f for f in diff_files]
            + [f.get("filename") for f in pr_files_raw if isinstance(f, dict) and f.get("filename")]
        )
    )

    files_changed_count = len(file_paths)

    lines_added = diff_data.get("num_added_lines", 0)
    lines_deleted = diff_data.get("num_deleted_lines", 0)
    total_lines_changed = lines_added + lines_deleted

    commits = pr_data.get("commits", [])
    # GitHub raw PR JSON returns 'commits' as an int count; fetch_pr_details returns a list.
    # Handle both so the feature extractor is safe regardless of the data source.
    if isinstance(commits, int):
        commits_count = commits
    else:
        commits_count = len(commits)

    if lines_deleted > 0:
        additions_to_deletions_ratio = round(lines_added / lines_deleted, 4)
    elif lines_added > 0:
        additions_to_deletions_ratio = float(lines_added)
    else:
        additions_to_deletions_ratio = 0.0

    if files_changed_count > 0:
        average_changes_per_file = round(total_lines_changed / files_changed_count, 4)
    else:
        average_changes_per_file = 0.0

    test_files_changed = 0
    documentation_files_changed = 0
    config_files_changed = 0
    source_files_changed = 0
    file_type_counts: Dict[str, int] = {}

    for path in file_paths:
        category = _classify_file(path)
        if category == "test":
            test_files_changed += 1
        elif category == "doc":
            documentation_files_changed += 1
        elif category == "config":
            config_files_changed += 1
        else:
            source_files_changed += 1

        ext = os.path.splitext(path)[1].lstrip(".").lower()
        ext_key = ext if ext else "no_extension"
        file_type_counts[ext_key] = file_type_counts.get(ext_key, 0) + 1

    added_files = 0
    deleted_files = 0
    renamed_files = 0

    for file_info in pr_files_raw:
        if not isinstance(file_info, dict):
            continue
        status = file_info.get("status", "").lower()
        if status == "added":
            added_files += 1
        elif status in ("removed", "deleted"):
            deleted_files += 1
        elif status == "renamed":
            renamed_files += 1

    binary_files_changed = len(diff_data.get("binary_files", []))

    return {
        "files_changed": files_changed_count,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "total_lines_changed": total_lines_changed,
        "commits_count": commits_count,
        "additions_to_deletions_ratio": additions_to_deletions_ratio,
        "source_files_changed": source_files_changed,
        "test_files_changed": test_files_changed,
        "documentation_files_changed": documentation_files_changed,
        "config_files_changed": config_files_changed,
        "average_changes_per_file": average_changes_per_file,
        "binary_files_changed": binary_files_changed,
        "renamed_files": renamed_files,
        "deleted_files": deleted_files,
        "added_files": added_files,
        "file_type_counts": file_type_counts,
    }
