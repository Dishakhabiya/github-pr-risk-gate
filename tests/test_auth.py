from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from app.api.main import app

client = TestClient(app)


def test_auth_me_unauthenticated():
    """Test GET /api/auth/me when unauthenticated."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_auth_logout():
    """Test POST /api/auth/logout."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}

    # Verify /api/auth/me returns unauthenticated after logout
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {"authenticated": False}


def test_oauth_login_redirect():
    """Test GET /api/auth/github/login URL generation and 302 redirect."""
    with patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id_123",
            "GITHUB_OAUTH_REDIRECT_URI": "http://localhost:8000/api/auth/github/callback",
        },
    ):
        response = client.get("/api/auth/github/login", follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("location")
        assert location is not None
        assert "https://github.com/login/oauth/authorize" in location
        assert "client_id=test_client_id_123" in location
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauth%2Fgithub%2Fcallback" in location or "redirect_uri=http://localhost:8000/api/auth/github/callback" in location
        assert "scope=read%3Auser" in location or "scope=read:user" in location


def test_oauth_callback_error_handling_missing_code():
    """Test callback error handling when code is missing or error is returned."""
    response = client.get(
        "/api/auth/github/callback?error=access_denied&error_description=User+canceled",
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers.get("location")
    assert location is not None
    assert "auth_error=User+canceled" in location or "auth_error=" in location


def test_oauth_callback_error_handling_token_exchange_failure():
    """Test callback error handling when GitHub token exchange fails."""
    mock_post_resp = MagicMock()
    mock_post_resp.ok = False
    mock_post_resp.status_code = 400

    with patch("requests.post", return_value=mock_post_resp), patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id_123",
            "GITHUB_OAUTH_CLIENT_SECRET": "test_secret_456",
        },
    ):
        response = client.get(
            "/api/auth/github/callback?code=mock_code_123",
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location")
        assert "auth_error=token_exchange_failed" in location


def test_oauth_callback_success_flow():
    """Test complete OAuth callback success flow with mocked GitHub responses."""
    mock_token_resp = MagicMock()
    mock_token_resp.ok = True
    mock_token_resp.json.return_value = {"access_token": "gho_mock_access_token_789"}

    mock_user_resp = MagicMock()
    mock_user_resp.ok = True
    mock_user_resp.json.return_value = {
        "login": "octocat",
        "name": "Monalisa Octocat",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
    }

    with patch("requests.post", return_value=mock_token_resp) as mock_post, patch(
        "requests.get", return_value=mock_user_resp
    ) as mock_get, patch.dict(
        "os.environ",
        {
            "GITHUB_OAUTH_CLIENT_ID": "test_client_id_123",
            "GITHUB_OAUTH_CLIENT_SECRET": "test_secret_456",
        },
    ):
        # 1. Trigger callback
        response = client.get(
            "/api/auth/github/callback?code=valid_oauth_code",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers.get("location") == "http://localhost:5173"

        # Verify token exchange request arguments (confirm secret wasn't exposed to client)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["data"]["client_id"] == "test_client_id_123"
        assert kwargs["data"]["client_secret"] == "test_secret_456"
        assert kwargs["data"]["code"] == "valid_oauth_code"

        # Verify user profile request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer gho_mock_access_token_789"

        # 2. Check /api/auth/me with session cookie
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["authenticated"] is True
        assert me_data["login"] == "octocat"
        assert me_data["name"] == "Monalisa Octocat"
        assert me_data["avatar_url"] == "https://github.com/images/error/octocat_happy.gif"
