from typing import Any, Dict, Optional
from app.github.client import GitHubClient


class GitHubCommitService:
    """Service to fetch and process GitHub commit information for analysis."""

    def __init__(self, client: Optional[GitHubClient] = None):
        self.client = client

    def _get_client(self) -> GitHubClient:
        if self.client is not None:
            return self.client
        return GitHubClient()

    def fetch_commit_details(
        self, owner: str, repository: str, commit_sha: str
    ) -> Dict[str, Any]:
        """Fetch complete structured commit details including metadata, files, and diff.

        Args:
            owner: Repository owner (e.g., 'octocat').
            repository: Repository name or 'owner/repo' path.
            commit_sha: Full or short commit SHA.

        Returns:
            Dict containing structured commit details formatted for features & preprocessing.
        """
        repo_name = repository.split("/")[-1] if "/" in repository else repository
        client = self._get_client()

        # 1. Validate authentication
        client.validate_auth()

        # 2. Fetch commit metadata & files
        commit_info = client.get_commit(owner, repo_name, commit_sha)
        full_sha = commit_info.get("sha", commit_sha)
        commit_obj = commit_info.get("commit", {}) if isinstance(commit_info.get("commit"), dict) else {}
        message = commit_obj.get("message", "")
        msg_lines = message.split("\n")
        title = msg_lines[0] if msg_lines else message
        body = "\n".join(msg_lines[1:]).strip() if len(msg_lines) > 1 else ""

        author_data = commit_obj.get("author", {}) if isinstance(commit_obj.get("author"), dict) else {}
        github_author = commit_info.get("author", {}) if isinstance(commit_info.get("author"), dict) else {}
        author_login = github_author.get("login") or author_data.get("name") or ""
        commit_date = author_data.get("date") or ""

        raw_files = commit_info.get("files", [])
        changed_files = [
            {
                "filename": file_item.get("filename"),
                "status": file_item.get("status"),
                "additions": file_item.get("additions", 0),
                "deletions": file_item.get("deletions", 0),
                "changes": file_item.get("changes", 0),
            }
            for file_item in raw_files if isinstance(file_item, dict)
        ]

        # 3. Fetch commit raw diff
        diff = client.get_commit_diff(owner, repo_name, commit_sha)

        return {
            "pr_id": full_sha[:7],
            "sha": full_sha,
            "short_sha": full_sha[:7],
            "repository": f"{owner}/{repo_name}",
            "title": title,
            "body": body,
            "full_message": message,
            "state": "committed",
            "author": author_login,
            "commit_date": commit_date,
            "commits": [{
                "sha": full_sha,
                "message": message,
                "author": author_login,
                "date": commit_date,
            }],
            "changed_files": changed_files,
            "diff": diff,
        }


def fetch_commit_details(
    owner: str, repository: str, commit_sha: str, client: Optional[GitHubClient] = None
) -> Dict[str, Any]:
    """Convenience wrapper for GitHubCommitService.fetch_commit_details."""
    service = GitHubCommitService(client=client)
    return service.fetch_commit_details(owner, repository, commit_sha)
