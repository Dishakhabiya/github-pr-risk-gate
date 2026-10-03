from typing import Any, Dict, List, Optional
from app.github.client import GitHubClient


class GitHubPRService:
    """Service to fetch and process GitHub PR information."""

    def __init__(self, client: Optional[GitHubClient] = None):
        self.client = client

    def _get_client(self) -> GitHubClient:
        if self.client is not None:
            return self.client
        return GitHubClient()

    def fetch_pr_details(
        self, owner: str, repository: str, pull_request_number: int
    ) -> Dict[str, Any]:
        """Fetch complete structured PR details including metadata, files, commits, and diff.

        Args:
            owner: Repository owner (e.g., 'octocat').
            repository: Repository name or 'owner/repo' path.
            pull_request_number: Pull Request number (e.g., 123).

        Returns:
            Dict containing structured PR details.
        """
        # Parse repo name if passed in 'owner/repo' format
        repo_name = repository.split("/")[-1] if "/" in repository else repository

        client = self._get_client()

        # 1. Validate authentication
        client.validate_auth()

        # 2. Fetch repository info
        repo_info = client.get_repository(owner, repo_name)
        repo_full_name = repo_info.get("full_name", f"{owner}/{repo_name}")

        # 3. Fetch PR metadata
        pr_metadata = client.get_pull_request(owner, repo_name, pull_request_number)

        # 4. Fetch changed files
        raw_files = client.get_pull_request_files(owner, repo_name, pull_request_number)
        changed_files: List[Dict[str, Any]] = [
            {
                "filename": file_item.get("filename"),
                "status": file_item.get("status"),
                "additions": file_item.get("additions", 0),
                "deletions": file_item.get("deletions", 0),
                "changes": file_item.get("changes", 0),
            }
            for file_item in raw_files
        ]

        # 5. Fetch commits
        raw_commits = client.get_pull_request_commits(owner, repo_name, pull_request_number)
        commits: List[Dict[str, Any]] = []
        for c in raw_commits:
            commit_data = c.get("commit", {}) if isinstance(c.get("commit"), dict) else {}
            author_data = commit_data.get("author", {}) if isinstance(commit_data.get("author"), dict) else {}
            github_author = c.get("author", {}) if isinstance(c.get("author"), dict) else {}

            author_name = author_data.get("name") or github_author.get("login") or ""
            commit_date = author_data.get("date") or ""

            commits.append({
                "sha": c.get("sha"),
                "message": commit_data.get("message", ""),
                "author": author_name,
                "date": commit_date,
            })

        # 6. Fetch complete PR diff
        diff = client.get_pull_request_diff(owner, repo_name, pull_request_number)

        # Return structured response
        return {
            "pr_id": pr_metadata.get("number"),
            "repository": repo_full_name,
            "title": pr_metadata.get("title", ""),
            "body": pr_metadata.get("body") or "",
            "state": pr_metadata.get("state", ""),
            "author": (pr_metadata.get("user") or {}).get("login", "")
            if isinstance(pr_metadata.get("user"), dict)
            else "",
            "base_branch": (pr_metadata.get("base") or {}).get("ref", "")
            if isinstance(pr_metadata.get("base"), dict)
            else "",
            "head_branch": (pr_metadata.get("head") or {}).get("ref", "")
            if isinstance(pr_metadata.get("head"), dict)
            else "",
            "commits": commits,
            "changed_files": changed_files,
            "diff": diff,
        }


def fetch_pr_details(
    owner: str, repository: str, pull_request_number: int, client: Optional[GitHubClient] = None
) -> Dict[str, Any]:
    """Convenience wrapper for GitHubPRService.fetch_pr_details."""
    service = GitHubPRService(client=client)
    return service.fetch_pr_details(owner, repository, pull_request_number)
