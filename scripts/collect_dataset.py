import argparse
import csv
import os
import sys
from typing import Any, Dict, List

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.dataset.collector import DatasetCollector
from app.dataset.labeler import (
    assign_risk_labels,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    METADATA_COLUMNS,
    OUTCOME_COLUMNS,
)
from app.github.client import GitHubClient



def build_dataframe_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure records contain all defined columns in the exact schema order."""
    all_columns = METADATA_COLUMNS + FEATURE_COLUMNS + OUTCOME_COLUMNS + [LABEL_COLUMN]
    ordered_records = []
    for r in records:
        row = {col: r.get(col, 0 if col in FEATURE_COLUMNS + OUTCOME_COLUMNS + [LABEL_COLUMN] else "") for col in all_columns}
        ordered_records.append(row)
    return ordered_records


def save_dataset_csv(records: List[Dict[str, Any]], output_path: str) -> None:
    """Save records to CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_columns = METADATA_COLUMNS + FEATURE_COLUMNS + OUTCOME_COLUMNS + [LABEL_COLUMN]

    ordered_rows = build_dataframe_rows(records)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        writer.writerows(ordered_rows)


def main():
    parser = argparse.ArgumentParser(description="Collect and build historical PR ML training dataset.")
    parser.add_argument(
        "--prs-per-repo",
        type=int,
        default=500,
        help="Number of closed PRs to collect per repository (default: 500).",
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        default=["kubernetes/kubernetes", "tensorflow/tensorflow", "microsoft/vscode"],
        help="List of owner/repo targets.",
    )
    parser.add_argument(
        "--percentile",
        type=float,
        default=80.0,
        help="Percentile threshold for high review-effort risk label (default: 80.0).",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="data/historical_prs.csv",
        help="Path for output dataset CSV file.",
    )

    args = parser.parse_args()

    print(f"=== Historical PR Dataset Collector ===")
    print(f"Target repositories: {args.repos}")
    print(f"Target PRs per repo: {args.prs_per_repo}")
    print(f"Percentile threshold: {args.percentile}th percentile\n")

    client = GitHubClient()
    collector = DatasetCollector(client=client, raw_dir="data/raw")

    all_records: List[Dict[str, Any]] = []
    repo_counts: Dict[str, int] = {}

    for repo_full_name in args.repos:
        if "/" not in repo_full_name:
            print(f"Skipping invalid repo name: {repo_full_name}")
            continue

        owner, repo = repo_full_name.split("/", 1)
        print(f"Collecting PRs for {owner}/{repo} (target: {args.prs_per_repo})...")
        records = collector.collect_repository_prs(owner, repo, max_prs=args.prs_per_repo)
        repo_counts[repo_full_name] = len(records)
        all_records.extend(records)
        print(f"Collected {len(records)} valid PR records for {owner}/{repo}.")

    if not all_records:
        print("\nNo records collected. Exiting.")
        sys.exit(0)

    # Label calculation via percentile threshold
    labeled_records, threshold_val = assign_risk_labels(
        all_records, percentile_threshold=args.percentile
    )

    # Save to CSV
    save_dataset_csv(labeled_records, args.output_csv)

    high_count = sum(1 for r in labeled_records if r.get(LABEL_COLUMN) == 1)
    low_count = sum(1 for r in labeled_records if r.get(LABEL_COLUMN) == 0)

    print("\n================ DATASET COLLECTION SUMMARY ================")
    print(f"Total PRs processed: {len(labeled_records)}")
    for repo_name, count in repo_counts.items():
        print(f"  - {repo_name}: {count} PRs")
    print(f"Review Effort Score Threshold ({args.percentile}th percentile): {threshold_val:.2f}")
    print(f"Risk Labels:")
    print(f"  - 0 (LOW RISK):  {low_count} ({low_count/len(labeled_records)*100:.1f}%)")
    print(f"  - 1 (HIGH RISK): {high_count} ({high_count/len(labeled_records)*100:.1f}%)")
    print(f"Dataset saved to: {args.output_csv}")
    print("============================================================\n")


if __name__ == "__main__":
    main()
