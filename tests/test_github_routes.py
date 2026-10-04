from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from app.api.main import app

client = TestClient(app)


def test_get_user_repos_unauthenticated():
    """Test GET /api/github/repos when unauthenticated returns 401."""
    response = client.get("/api/github/repos")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_get_repo_pulls_unauthenticated():
    """Test GET /api/github/repos/{owner}/{repo}/pulls when unauthenticated returns 401."""
    response = client.get("/api/github/repos/owner/repo/pulls")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_get_user_repos_authenticated():
    """Test GET /api/github/repos when authenticated."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {
        "login": "octocat",
        "name": "Monalisa Octocat",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
    }

    mock_github_repos = MagicMock(ok=True)
    mock_github_repos.json.return_value = [
        {
            "full_name": "octocat/Hello-World",
            "name": "Hello-World",
            "owner": {"login": "octocat"},
            "private": False,
            "html_url": "https://github.com/octocat/Hello-World",
        },
        {
            "full_name": "octocat/Spoon-Knife",
            "name": "Spoon-Knife",
            "owner": {"login": "octocat"},
            "private": True,
            "html_url": "https://github.com/octocat/Spoon-Knife",
        },
    ]

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", side_effect=[mock_user_resp, mock_github_repos]
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        # 1. Login via callback to populate session
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        # 2. Fetch repos
        repos_resp = auth_client.get("/api/github/repos")
        assert repos_resp.status_code == 200
        repos = repos_resp.json()
        assert len(repos) == 2
        assert repos[0]["full_name"] == "octocat/Hello-World"
        assert repos[1]["private"] is True


def test_get_repo_pulls_authenticated():
    """Test GET /api/github/repos/{owner}/{repo}/pulls when authenticated."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {"login": "octocat"}

    mock_github_pulls = MagicMock(ok=True)
    mock_github_pulls.json.return_value = [
        {
            "number": 1,
            "title": "Fix bug in parser",
            "state": "open",
            "user": {"login": "octocat"},
            "html_url": "https://github.com/octocat/Hello-World/pull/1",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
    ]

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", side_effect=[mock_user_resp, mock_github_pulls]
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        pulls_resp = auth_client.get("/api/github/repos/octocat/Hello-World/pulls")
        assert pulls_resp.status_code == 200
        pulls = pulls_resp.json()
        assert len(pulls) == 1
        assert pulls[0]["number"] == 1
        assert pulls[0]["title"] == "Fix bug in parser"


def test_get_repo_pulls_not_found():
    """Test GET /api/github/repos/{owner}/{repo}/pulls returns 404 for missing repo."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {"login": "octocat"}

    mock_404_resp = MagicMock(ok=False, status_code=404)

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", side_effect=[mock_user_resp, mock_404_resp]
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        pulls_resp = auth_client.get("/api/github/repos/nonexistent/repo/pulls")
        assert pulls_resp.status_code == 404


def test_get_repo_pulls_zero_prs():
    """Test GET /api/github/repos/{owner}/{repo}/pulls returns [] when repository has zero PRs."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {"login": "octocat"}

    mock_empty_pulls = MagicMock(ok=True)
    mock_empty_pulls.json.return_value = []

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", side_effect=[mock_user_resp, mock_empty_pulls]
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        pulls_resp = auth_client.get("/api/github/repos/Dishakhabiya/Leetcode/pulls")
        assert pulls_resp.status_code == 200
        pulls = pulls_resp.json()
        assert isinstance(pulls, list)
        assert len(pulls) == 0



def test_logout_clears_repo_access():
    """Test that logout clears user session and subsequent repo access returns 401."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {"login": "octocat"}

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", return_value=mock_user_resp
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        # Logout
        auth_client.post("/api/auth/logout")

        # Subsequent repo access fails with 401
        repos_resp = auth_client.get("/api/github/repos")
        assert repos_resp.status_code == 401


def test_get_repo_commits_authenticated():
    """Test GET /api/github/repos/{owner}/{repo}/commits when authenticated."""
    mock_token_resp = MagicMock(ok=True)
    mock_token_resp.json.return_value = {"access_token": "mock_token_xyz"}

    mock_user_resp = MagicMock(ok=True)
    mock_user_resp.json.return_value = {"login": "octocat"}

    mock_github_commits = MagicMock(ok=True)
    mock_github_commits.json.return_value = [
        {
            "sha": "a1b2c3d4e5f67890",
            "commit": {
                "message": "Initial commit\n\nDetailed body text",
                "author": {"name": "Monalisa Octocat", "date": "2026-01-01T00:00:00Z"},
            },
            "author": {"login": "octocat"},
            "html_url": "https://github.com/octocat/Hello-World/commit/a1b2c3d4e5f67890",
        }
    ]

    with patch("requests.post", return_value=mock_token_resp), patch(
        "requests.get", side_effect=[mock_user_resp, mock_github_commits]
    ), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        },
    ):
        auth_client = TestClient(app)
        auth_client.get("/api/auth/github/callback?code=valid_code")

        commits_resp = auth_client.get("/api/github/repos/octocat/Hello-World/commits")
        assert commits_resp.status_code == 200
        commits = commits_resp.json()
        assert len(commits) == 1
        assert commits[0]["sha"] == "a1b2c3d4e5f67890"
        assert commits[0]["short_sha"] == "a1b2c3d"
        assert commits[0]["message"] == "Initial commit"
        assert commits[0]["author"]["login"] == "octocat"

