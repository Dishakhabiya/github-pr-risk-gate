import json
import os
from typing import Any, Dict, List, Optional, Set

from app.dataset.labeler import (
    calculate_review_effort_score,
    check_has_linked_issue,
    FEATURE_COLUMNS,
    METADATA_COLUMNS,
    OUTCOME_COLUMNS,
)
from app.features.extractor import extract_features
from app.github.client import GitHubClient
from app.github.pr_service import fetch_pr_details
from app.preprocessing.diff_processor import preprocess_diff

BOT_LOGINS: Set[str] = {
    "dependabot[bot]",
    "renovate[bot]",
    "k8s-ci-robot",
    "k8s-triage-robot",
    "tensorflow-jenkins",
    "msftbot",
    "codecov[bot]",
    "greenkeeper[bot]",
    "bot",
}


def is_bot_author(author_login: Optional[str]) -> bool:
    """Check if the PR author is an automated bot account.

    Args:
        author_login: GitHub login username.

    Returns:
        True if the author is a recognized bot, False otherwise.
    """
    if not author_login:
        return False

    login_lower = author_login.lower()
    if login_lower.endswith("[bot]") or login_lower in BOT_LOGINS:
        return True

    if "bot" in login_lower:
        return True

    return False


class DatasetCollector:
    """Collector for historical PR dataset generation."""

    def __init__(self, client: Optional[GitHubClient] = None, raw_dir: str = "data/raw"):
        self.client = client or GitHubClient()
        self.raw_dir = raw_dir
        os.makedirs(self.raw_dir, exist_ok=True)

    def _get_cache_file_path(self, owner: str, repo: str) -> str:
        safe_repo = repo.replace("/", "_")
        return os.path.join(self.raw_dir, f"{owner}_{safe_repo}_prs.jsonl")

    def _load_cached_records(self, cache_path: str) -> List[Dict[str, Any]]:
        records = []
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line.strip()))
        return records

    def process_single_pr(
        self, owner: str, repo: str, pr_summary: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Fetch, preprocess, and extract features for a single PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_summary: Basic PR item dict from GitHub API list response.

        Returns:
            Structured record dict or None if invalid/bot.
        """
        user_info = pr_summary.get("user") or {}
        author = user_info.get("login", "")

        if is_bot_author(author):
            return None

        pr_number = pr_summary.get("number")
        if not pr_number:
            return None

        # Fetch full details using US-01 service
        try:
            pr_data = fetch_pr_details(owner, repo, pr_number, client=self.client)
            full_pr = self.client.get_pull_request(owner, repo, pr_number)
            raw_reviews = self.client.get_pull_request_reviews(owner, repo, pr_number)
        except Exception as e:
            # Handle API retrieval errors or missing resources gracefully
            return None

        # Skip empty PRs without changed files
        if not pr_data.get("changed_files") and not pr_data.get("diff"):
            return None

        # US-02 diff preprocessing
        diff_data = preprocess_diff(pr_data.get("diff", ""))

        # US-03 feature extraction (Creation-time inputs)
        features = extract_features(pr_data, diff_data)

        # Creation-time text features
        title = pr_data.get("title") or ""
        body = pr_data.get("body") or ""
        title_length = len(title)
        body_length = len(body)
        has_linked_issue = check_has_linked_issue(title, body)

        # Outcome fields (Post-creation lifecycle data)
        review_comments_count = full_pr.get("review_comments", 0)
        issue_comments_count = full_pr.get("comments", 0)

        changes_requested_count = sum(
            1 for r in raw_reviews if (r.get("state") or "").upper() == "CHANGES_REQUESTED"
        )
        approved_count = sum(
            1 for r in raw_reviews if (r.get("state") or "").upper() == "APPROVED"
        )
        commented_count = sum(
            1 for r in raw_reviews if (r.get("state") or "").upper() == "COMMENTED"
        )
        review_count = len(raw_reviews)
        merged = bool(full_pr.get("merged", False))

        review_effort_score = calculate_review_effort_score(
            review_comments_count=review_comments_count,
            changes_requested_count=changes_requested_count,
            issue_comments_count=issue_comments_count,
        )

        record: Dict[str, Any] = {
            "repository": f"{owner}/{repo}",
            "pr_id": pr_number,
            "created_at": full_pr.get("created_at", ""),
            "title_length": title_length,
            "body_length": body_length,
            "has_linked_issue": has_linked_issue,
            "review_comments_count": review_comments_count,
            "issue_comments_count": issue_comments_count,
            "changes_requested_count": changes_requested_count,
            "approved_count": approved_count,
            "review_count": review_count,
            "review_effort_score": review_effort_score,
            "merged": merged,
        }

        # Merge extracted features
        record.update(features)
        return record

    def collect_repository_prs(
        self, owner: str, repo: str, max_prs: int = 500
    ) -> List[Dict[str, Any]]:
        """Collect closed PRs for a repository up to max_prs.

        Args:
            owner: Repository owner.
            repo: Repository name.
            max_prs: Target number of valid PR records to collect.

        Returns:
            List of structured PR records.
        """
        cache_path = self._get_cache_file_path(owner, repo)
        existing_records = self._load_cached_records(cache_path)
        existing_pr_ids = {r["pr_id"] for r in existing_records}

        if len(existing_records) >= max_prs:
            return existing_records[:max_prs]

        collected_records: List[Dict[str, Any]] = list(existing_records)

        page = 1
        per_page = 100

        while len(collected_records) < max_prs:
            try:
                prs_page = self.client.list_closed_pull_requests(
                    owner, repo, page=page, per_page=per_page
                )
            except Exception:
                break

            if not prs_page:
                break

            for pr_item in prs_page:
                pr_number = pr_item.get("number")
                if not pr_number or pr_number in existing_pr_ids:
                    continue

                record = self.process_single_pr(owner, repo, pr_item)
                if record is not None:
                    collected_records.append(record)
                    existing_pr_ids.add(pr_number)

                    # Save incrementally to cache file
                    with open(cache_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record) + "\n")

                    if len(collected_records) >= max_prs:
                        break

            page += 1

        return collected_records[:max_prs]
