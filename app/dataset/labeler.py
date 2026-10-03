import re
from typing import Any, Dict, List, Tuple

# Explicit schema column definitions enforcing separation to prevent data leakage
METADATA_COLUMNS = [
    "repository",
    "pr_id",
    "created_at",
]

FEATURE_COLUMNS = [
    "files_changed",
    "lines_added",
    "lines_deleted",
    "total_lines_changed",
    "commits_count",
    "additions_to_deletions_ratio",
    "source_files_changed",
    "test_files_changed",
    "documentation_files_changed",
    "config_files_changed",
    "average_changes_per_file",
    "binary_files_changed",
    "renamed_files",
    "deleted_files",
    "added_files",
    "title_length",
    "body_length",
    "has_linked_issue",
]

OUTCOME_COLUMNS = [
    "review_comments_count",
    "issue_comments_count",
    "changes_requested_count",
    "approved_count",
    "review_count",
    "review_effort_score",
    "merged",
]

LABEL_COLUMN = "risk_label"


def calculate_review_effort_score(
    review_comments_count: int,
    changes_requested_count: int,
    issue_comments_count: int = 0,
) -> float:
    """Calculate the continuous review-effort score for a PR.

    Formula:
        score = (inline_review_comments * 1.0) + (changes_requested * 3.0) + (issue_comments * 0.5)

    Rationale:
        - Inline code comments represent targeted line-by-line review iterations.
        - CHANGES_REQUESTED decisions represent significant blocking rework rounds (3x weight).
        - General issue comments represent general conversation overhead (0.5x weight).
    """
    inline_weight = 1.0
    changes_requested_weight = 3.0
    issue_comment_weight = 0.5

    score = (
        (review_comments_count * inline_weight)
        + (changes_requested_count * changes_requested_weight)
        + (issue_comments_count * issue_comment_weight)
    )
    return round(score, 2)


def _compute_percentile(values: List[float], percentile: float) -> float:
    """Compute the percentile value of a list of floats using linear interpolation."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])

    k = (n - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c >= n:
        return float(sorted_values[-1])
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return float(d0 + d1)


def assign_risk_labels(
    records: List[Dict[str, Any]], percentile_threshold: float = 80.0
) -> Tuple[List[Dict[str, Any]], float]:
    """Calculate review-effort score for each record and assign risk_label based on a percentile threshold.

    Args:
        records: List of processed PR feature & metric dictionaries.
        percentile_threshold: Target percentile threshold (e.g. 80.0 for 80th percentile).

    Returns:
        Tuple of (labeled_records, threshold_value).
    """
    if not records:
        return [], 0.0

    scores = [
        r.get(
            "review_effort_score",
            calculate_review_effort_score(
                r.get("review_comments_count", 0),
                r.get("changes_requested_count", 0),
                r.get("issue_comments_count", 0),
            ),
        )
        for r in records
    ]

    for record, score in zip(records, scores):
        record["review_effort_score"] = score

    # Calculate percentile threshold using pure Python
    threshold = _compute_percentile(scores, percentile_threshold)

    # Assign risk label (1 = HIGH RISK, 0 = LOW RISK)
    for record in records:
        score = record["review_effort_score"]
        if score >= threshold and score > 0:
            record[LABEL_COLUMN] = 1
        else:
            record[LABEL_COLUMN] = 0

    return records, threshold


def check_has_linked_issue(title: str, body: str) -> int:
    """Check if title or body references an issue (e.g., #123, Fixes #456, Resolves #789)."""
    text = f"{title or ''} {body or ''}".lower()
    pattern = r"(?:fixes|resolves|closes|refs|issue)?\s*#\d+"
    return 1 if re.search(pattern, text) else 0
