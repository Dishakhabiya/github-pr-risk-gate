import os
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

from app.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

load_dotenv()


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    def __init__(self, token: Optional[str] = None, api_url: Optional[str] = None):
        raw_token = token if token is not None else os.getenv("GITHUB_TOKEN")
        if not raw_token or not raw_token.strip():
            raise GitHubAuthError(
                "GitHub token is missing. Please set GITHUB_TOKEN in environment or .env file."
            )

        self.token = raw_token.strip()
        base_url = api_url or os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.api_url = base_url.rstrip("/")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-pr-risk-gate",
        })

    def _handle_response(
        self, response: requests.Response, resource_description: str = "Resource"
    ) -> requests.Response:
        if response.status_code == 401:
            raise GitHubAuthError("Invalid or expired GitHub token.")

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0" or "rate limit" in response.text.lower():
                raise GitHubRateLimitError("GitHub API rate limit exceeded.")
            raise GitHubAuthError("Access forbidden or insufficient token permissions.")

        if response.status_code == 404:
            raise GitHubNotFoundError(f"{resource_description} not found.")

        if response.status_code == 406:
            try:
                error_data = response.json()
                msg = error_data.get("message", "")
            except Exception:
                msg = response.text
            if "too_large" in msg or "exceeded" in msg or "maximum number of lines" in msg:
                raise ValueError(f"{resource_description} is too large for the GitHub API to process (e.g. >20,000 lines).")
            raise GitHubAPIError(f"GitHub API request failed with status code 406: {msg}")

        if not response.ok:
            raise GitHubAPIError(
                f"GitHub API request failed with status code {response.status_code}."
            )

        return response

    def validate_auth(self) -> Dict[str, Any]:
        """Validate GitHub authentication by fetching authenticated user details."""
        url = f"{self.api_url}/user"
        response = self.session.get(url)
        res = self._handle_response(response, resource_description="User profile")
        return res.json()

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository information."""
        url = f"{self.api_url}/repos/{owner}/{repo}"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Repository '{owner}/{repo}'"
        )
        return res.json()

    def get_pull_request(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Fetch pull request metadata."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Pull Request #{pull_number} in '{owner}/{repo}'"
        )
        return res.json()

    def get_pull_request_files(
        self, owner: str, repo: str, pull_number: int
    ) -> List[Dict[str, Any]]:
        """Fetch changed files for a pull request."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Files for PR #{pull_number} in '{owner}/{repo}'"
        )
        return res.json()

    def get_pull_request_commits(
        self, owner: str, repo: str, pull_number: int
    ) -> List[Dict[str, Any]]:
        """Fetch commits for a pull request."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/commits"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Commits for PR #{pull_number} in '{owner}/{repo}'"
        )
        return res.json()

    def get_pull_request_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """Fetch raw diff string for a pull request."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        response = self.session.get(url, headers=headers)
        res = self._handle_response(
            response, resource_description=f"Diff for PR #{pull_number} in '{owner}/{repo}'"
        )
        return res.text

    def list_closed_pull_requests(
        self, owner: str, repo: str, page: int = 1, per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """List closed pull requests for a repository."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls"
        params = {"state": "closed", "sort": "created", "direction": "desc", "page": page, "per_page": per_page}
        response = self.session.get(url, params=params)
        res = self._handle_response(
            response, resource_description=f"Closed PRs page {page} for '{owner}/{repo}'"
        )
        return res.json()

    def get_pull_request_reviews(
        self, owner: str, repo: str, pull_number: int
    ) -> List[Dict[str, Any]]:
        """Fetch reviews submitted for a pull request."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Reviews for PR #{pull_number} in '{owner}/{repo}'"
        )
        return res.json()

    def get_repository_tree(
        self, owner: str, repo: str, tree_sha: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """Fetch repository tree."""
        url = f"{self.api_url}/repos/{owner}/{repo}/git/trees/{tree_sha}"
        params = {"recursive": "1"} if recursive else {}
        response = self.session.get(url, params=params)
        res = self._handle_response(
            response, resource_description=f"Tree '{tree_sha}' for '{owner}/{repo}'"
        )
        return res.json()

    def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> Dict[str, Any]:
        """Fetch file content from repository."""
        url = f"{self.api_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        response = self.session.get(url, params=params)
        res = self._handle_response(
            response, resource_description=f"File '{path}' for '{owner}/{repo}' at '{ref}'"
        )
        return res.json()

    def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """Fetch commit details including files and stats."""
        url = f"{self.api_url}/repos/{owner}/{repo}/commits/{sha}"
        response = self.session.get(url)
        res = self._handle_response(
            response, resource_description=f"Commit '{sha}' in '{owner}/{repo}'"
        )
        return res.json()

    def get_commit_diff(self, owner: str, repo: str, sha: str) -> str:
        """Fetch raw diff string for a commit."""
        url = f"{self.api_url}/repos/{owner}/{repo}/commits/{sha}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        response = self.session.get(url, headers=headers)
        res = self._handle_response(
            response, resource_description=f"Diff for commit '{sha}' in '{owner}/{repo}'"
        )
        return res.text

    def post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """US-16: Post a comment on an issue or pull request."""
        url = f"{self.api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        payload = {"body": body}
        response = self.session.post(url, json=payload)
        res = self._handle_response(
            response, resource_description=f"Comment on PR #{issue_number} in '{owner}/{repo}'"
        )
        return res.json()
