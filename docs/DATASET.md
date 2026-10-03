# Historical ML Training Dataset Documentation

## 1. Data Sources
Historical Pull Requests are collected from three major open-source GitHub repositories:
- `kubernetes/kubernetes` (Go - Cloud Native Infrastructure)
- `tensorflow/tensorflow` (C++ / Python - Machine Learning Framework)
- `microsoft/vscode` (TypeScript - Desktop & Web IDE)

## 2. Rationale for Repository Selection
Using these three repositories ensures high linguistic and structural diversity in our training dataset:
- **Ecosystem Variety**: Covers Go, C++, Python, and TypeScript codebase patterns.
- **Workflow Diversity**: Captures different PR review standards, commit frequencies, and team collaboration styles.
- **High Quality Data**: Large-scale repositories with rich review activity, explicit approvals, and inline discussions.

## 3. Collected Fields & Schema Overview

The final dataset (`data/historical_prs.csv`) contains three cleanly separated column groups:

### A. Metadata Identification Fields
- `repository`: Repository full name (`owner/repo`)
- `pr_id`: GitHub Pull Request number
- `created_at`: Creation timestamp (ISO8601)

### B. Model Input Features (Creation-Time Only)
Strictly generated from information available at the exact moment of PR creation:
- `files_changed`: Total count of modified/added/deleted files
- `lines_added`: Lines added count
- `lines_deleted`: Lines deleted count
- `total_lines_changed`: Sum of additions and deletions (`lines_added + lines_deleted`)
- `commits_count`: Number of initial commits in the PR
- `additions_to_deletions_ratio`: Ratio of added to deleted lines
- `source_files_changed`: Count of source code files
- `test_files_changed`: Count of test files
- `documentation_files_changed`: Count of documentation files
- `config_files_changed`: Count of configuration/build files
- `average_changes_per_file`: Average churn density per file
- `binary_files_changed`: Count of binary files
- `renamed_files`: Count of renamed files
- `deleted_files`: Count of deleted files
- `added_files`: Count of newly added files
- `title_length`: Character length of PR title
- `body_length`: Character length of PR body
- `has_linked_issue`: Binary indicator (1 if issue/fix reference found in title/body, else 0)

### C. Post-Creation Outcome / Review Overhead Fields (Outcome Data)
> **CRITICAL**: These fields occur AFTER PR creation and MUST NOT be used as model input features to prevent Data Leakage.

- `review_comments_count`: Count of inline code review comments
- `issue_comments_count`: Count of general conversation comments
- `changes_requested_count`: Count of `CHANGES_REQUESTED` review decisions
- `approved_count`: Count of `APPROVED` review decisions
- `review_count`: Total review decisions submitted
- `merged`: Boolean flag indicating if PR was merged
- `review_effort_score`: Continuous weighted score calculated from review overhead

### D. Target Label
- `risk_label`: Binary target classification (`0` = LOW REVIEW-EFFORT RISK, `1` = HIGH REVIEW-EFFORT RISK)

## 4. Review-Effort Score Calculation

The review-effort score measures the reviewer intervention and interaction overhead required before PR resolution:

$$\text{score} = (\text{inline\_review\_comments} \times 1.0) + (\text{changes\_requested} \times 3.0) + (\text{issue\_comments} \times 0.5)$$

- **Inline review comments (1.0x)**: Direct reviewer feedback requiring code adjustments.
- **CHANGES_REQUESTED (3.0x)**: Formal review rejections indicating significant rework rounds.
- **Issue comments (0.5x)**: General discussion and administrative overhead.

## 5. Risk Label Assignment & 80th Percentile Threshold
- **Threshold Determination**: The cutoff is dynamically calculated as the **80th percentile** of `review_effort_score` across the dataset.
- **Why 80th Percentile?**: Captures the top 20% most review-intensive PRs as **HIGH RISK (1)**, while treating standard routine PRs (bottom 80%) as **LOW RISK (0)**.
- **Configurable**: The percentile cutoff can be adjusted using the `--percentile` CLI flag.

## 6. How to Run the Collector

To run historical data collection with the default 500 PRs per repository:

```bash
python scripts/collect_dataset.py --prs-per-repo 500 --percentile 80.0
```

To run a fast test collection (e.g. 5 PRs per repo):

```bash
python scripts/collect_dataset.py --prs-per-repo 5
```

Output is saved to `data/historical_prs.csv`.

## 7. Known GitHub API & Diff Limitations
1. **API Rate Limiting**: Authenticated requests are limited to 5,000 requests/hour per PAT. The collector caches raw PRs in `data/raw/` to ensure resumability.
2. **Truncated Diff Patches**: GitHub API omits raw diff patches for very large PRs (> 300 files or > 10,000 lines). In these cases, file metadata additions/deletions from US-01 are used.
3. **Bot Account Rejection**: Automated bot PRs (e.g., Dependabot, Renovate) are automatically filtered out to ensure realistic human developer PR distributions.
