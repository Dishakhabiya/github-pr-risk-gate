import os
from unittest.mock import MagicMock, patch
import pytest

from app.github.client import GitHubClient
from app.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.github.pr_service import GitHubPRService, fetch_pr_details


@pytest.fixture
def mock_env_token(monkeypatch):
    """Provide a fake GITHUB_TOKEN environment variable for tests."""
    fake_token = "fake_github_token_123456789"
    monkeypatch.setenv("GITHUB_TOKEN", fake_token)
    return fake_token


class TestGitHubClient:
    def test_missing_token(self, monkeypatch):
        """Test that missing GITHUB_TOKEN raises GitHubAuthError."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(GitHubAuthError) as exc_info:
            GitHubClient(token="")
        assert "token is missing" in str(exc_info.value).lower()

    def test_authentication_valid(self, mock_env_token):
        """Test authentication validation with valid token."""
        client = GitHubClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "login": "testuser",
            "id": 1,
            "name": "Test User",
        }

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            user_info = client.validate_auth()
            mock_get.assert_called_once_with("https://api.github.com/user")
            assert user_info["login"] == "testuser"

    def test_authentication_invalid(self, mock_env_token):
        """Test 401 Unauthorized response raises GitHubAuthError."""
        client = GitHubClient()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.ok = False

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(GitHubAuthError) as exc_info:
                client.validate_auth()
            assert "invalid or expired github token" in str(exc_info.value).lower()

    def test_rate_limiting(self, mock_env_token):
        """Test 403 Rate Limit response raises GitHubRateLimitError."""
        client = GitHubClient()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.ok = False
        mock_response.headers = {"X-RateLimit-Remaining": "0"}
        mock_response.text = "API rate limit exceeded"

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(GitHubRateLimitError) as exc_info:
                client.get_repository("testowner", "testrepo")
            assert "rate limit exceeded" in str(exc_info.value).lower()

    def test_token_not_exposed_in_exceptions(self, mock_env_token):
        """Verify that secret token is never exposed in error messages."""
        secret_token = "secret_pat_987654321"
        client = GitHubClient(token=secret_token)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.ok = False

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(GitHubNotFoundError) as exc_info:
                client.get_repository("owner", "nonexistent")
            assert secret_token not in str(exc_info.value)


class TestPRService:
    def test_valid_pr(self, mock_env_token):
        """Test fetching a valid PR and assembling structured data."""
        client = GitHubClient()

        # Mock API responses
        res_user = MagicMock(status_code=200, ok=True)
        res_user.json.return_value = {"login": "octocat"}

        res_repo = MagicMock(status_code=200, ok=True)
        res_repo.json.return_value = {
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
        }

        res_pr = MagicMock(status_code=200, ok=True)
        res_pr.json.return_value = {
            "number": 1347,
            "title": "Amazing new feature",
            "body": "Please pull these changes.",
            "state": "open",
            "user": {"login": "octocat"},
            "base": {"ref": "main"},
            "head": {"ref": "new-topic"},
        }

        res_files = MagicMock(status_code=200, ok=True)
        res_files.json.return_value = [
            {
                "filename": "file1.py",
                "status": "modified",
                "additions": 10,
                "deletions": 2,
                "changes": 12,
            },
            {
                "filename": "file2.md",
                "status": "added",
                "additions": 5,
                "deletions": 0,
                "changes": 5,
            },
        ]

        res_commits = MagicMock(status_code=200, ok=True)
        res_commits.json.return_value = [
            {
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "commit": {
                    "message": "Fix all bugs",
                    "author": {"name": "Monalisa Octocat", "date": "2026-10-01T00:00:00Z"},
                },
            }
        ]

        res_diff = MagicMock(status_code=200, ok=True)
        res_diff.text = "diff --git a/file1.py b/file1.py\n+new line\n-old line"

        def mock_get(url, headers=None):
            if url.endswith("/user"):
                return res_user
            elif "/repos/octocat/Hello-World/pulls/1347/files" in url:
                return res_files
            elif "/repos/octocat/Hello-World/pulls/1347/commits" in url:
                return res_commits
            elif "/repos/octocat/Hello-World/pulls/1347" in url:
                if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                    return res_diff
                return res_pr
            elif "/repos/octocat/Hello-World" in url:
                return res_repo
            raise ValueError(f"Unexpected URL mocked: {url}")

        with patch.object(client.session, "get", side_effect=mock_get):
            pr_data = fetch_pr_details("octocat", "Hello-World", 1347, client=client)

            assert pr_data["pr_id"] == 1347
            assert pr_data["repository"] == "octocat/Hello-World"
            assert pr_data["title"] == "Amazing new feature"
            assert pr_data["body"] == "Please pull these changes."
            assert pr_data["state"] == "open"
            assert pr_data["author"] == "octocat"
            assert pr_data["base_branch"] == "main"
            assert pr_data["head_branch"] == "new-topic"
            assert len(pr_data["commits"]) == 1
            assert pr_data["commits"][0]["sha"] == "6dcb09b5b57875f334f61aebed695e2e4193db5e"
            assert pr_data["commits"][0]["author"] == "Monalisa Octocat"
            assert len(pr_data["changed_files"]) == 2
            assert pr_data["diff"] == "diff --git a/file1.py b/file1.py\n+new line\n-old line"

    def test_invalid_repository(self, mock_env_token):
        """Test fetching PR when repository does not exist."""
        client = GitHubClient()

        res_user = MagicMock(status_code=200, ok=True)
        res_user.json.return_value = {"login": "testuser"}

        res_repo_404 = MagicMock(status_code=404, ok=False)

        def mock_get(url, headers=None):
            if url.endswith("/user"):
                return res_user
            return res_repo_404

        with patch.object(client.session, "get", side_effect=mock_get):
            with pytest.raises(GitHubNotFoundError) as exc_info:
                fetch_pr_details("invalid_owner", "invalid_repo", 1, client=client)
            assert "repository 'invalid_owner/invalid_repo' not found" in str(exc_info.value).lower()

    def test_invalid_pr(self, mock_env_token):
        """Test fetching PR when repo exists but PR does not exist."""
        client = GitHubClient()

        res_user = MagicMock(status_code=200, ok=True)
        res_user.json.return_value = {"login": "testuser"}

        res_repo = MagicMock(status_code=200, ok=True)
        res_repo.json.return_value = {
            "name": "myrepo",
            "full_name": "owner/myrepo",
        }

        res_pr_404 = MagicMock(status_code=404, ok=False)

        def mock_get(url, headers=None):
            if url.endswith("/user"):
                return res_user
            elif url.endswith("/repos/owner/myrepo"):
                return res_repo
            return res_pr_404

        with patch.object(client.session, "get", side_effect=mock_get):
            with pytest.raises(GitHubNotFoundError) as exc_info:
                fetch_pr_details("owner", "myrepo", 999, client=client)
            assert "pull request #999" in str(exc_info.value).lower()

    def test_changed_file_parsing(self, mock_env_token):
        """Test that changed files are parsed accurately with all required fields."""
        client = GitHubClient()

        raw_files = [
            {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 42,
                "deletions": 10,
                "changes": 52,
                "patch": "@@ -1,3 +1,5 @@...",
            },
            {
                "filename": "tests/test_main.py",
                "status": "added",
                "additions": 15,
                "deletions": 0,
                "changes": 15,
            },
            {
                "filename": "docs/old.md",
                "status": "removed",
                "additions": 0,
                "deletions": 30,
                "changes": 30,
            },
        ]

        res_user = MagicMock(status_code=200, ok=True)
        res_repo = MagicMock(status_code=200, ok=True)
        res_repo.json.return_value = {"full_name": "owner/repo"}
        res_pr = MagicMock(status_code=200, ok=True)
        res_pr.json.return_value = {"number": 1, "title": "Test", "body": ""}
        res_files = MagicMock(status_code=200, ok=True)
        res_files.json.return_value = raw_files
        res_commits = MagicMock(status_code=200, ok=True)
        res_commits.json.return_value = []
        res_diff = MagicMock(status_code=200, ok=True)
        res_diff.text = ""

        def mock_get(url, headers=None):
            if url.endswith("/user"):
                return res_user
            elif "/files" in url:
                return res_files
            elif "/commits" in url:
                return res_commits
            elif url.endswith("/pulls/1"):
                if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                    return res_diff
                return res_pr
            elif url.endswith("/repos/owner/repo"):
                return res_repo
            return MagicMock(status_code=200, ok=True, json=lambda: {})

        with patch.object(client.session, "get", side_effect=mock_get):
            pr_data = fetch_pr_details("owner", "repo", 1, client=client)
            files = pr_data["changed_files"]
            assert len(files) == 3

            f1, f2, f3 = files
            assert f1 == {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 42,
                "deletions": 10,
                "changes": 52,
            }
            assert f2 == {
                "filename": "tests/test_main.py",
                "status": "added",
                "additions": 15,
                "deletions": 0,
                "changes": 15,
            }
            assert f3 == {
                "filename": "docs/old.md",
                "status": "removed",
                "additions": 0,
                "deletions": 30,
                "changes": 30,
            }
