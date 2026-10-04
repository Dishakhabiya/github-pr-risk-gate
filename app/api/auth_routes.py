import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
import requests

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/github/login")
def github_login() -> RedirectResponse:
    """Redirect the user to GitHub's OAuth authorization page."""
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
    redirect_uri = os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/auth/github/callback",
    )
    scope = "read:user"

    if not client_id:
        logger.error("GITHUB_OAUTH_CLIENT_ID is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth client ID is not configured.",
        )

    import urllib.parse
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
    }
    auth_url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> RedirectResponse:
    """Handle OAuth authorization callback from GitHub."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    # Handle error or missing code from GitHub authorization redirect cleanly
    if error or not code:
        err_msg = error_description or error or "authorization_denied"
        logger.warning("GitHub OAuth callback error: %s", err_msg)
        return RedirectResponse(
            url=f"{frontend_url}?auth_error={err_msg}",
            status_code=status.HTTP_302_FOUND,
        )

    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")
    redirect_uri = os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/auth/github/callback",
    )

    if not client_id or not client_secret:
        logger.error("GitHub OAuth credentials are not properly configured.")
        return RedirectResponse(
            url=f"{frontend_url}?auth_error=server_configuration_error",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        # 1. Exchange authorization code for access token on backend
        token_response = requests.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=10,
        )

        if not token_response.ok:
            logger.error("Token exchange failed with status %s", token_response.status_code)
            return RedirectResponse(
                url=f"{frontend_url}?auth_error=token_exchange_failed",
                status_code=status.HTTP_302_FOUND,
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            token_err = (
                token_data.get("error_description")
                or token_data.get("error")
                or "invalid_token_response"
            )
            logger.error("Token exchange response missing access token: %s", token_err)
            return RedirectResponse(
                url=f"{frontend_url}?auth_error={token_err}",
                status_code=status.HTTP_302_FOUND,
            )

        # 2. Fetch authenticated GitHub user's basic profile
        user_response = requests.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "github-pr-risk-gate",
                "Accept": "application/json",
            },
            timeout=10,
        )

        if not user_response.ok:
            logger.error("Failed to fetch user profile: %s", user_response.status_code)
            return RedirectResponse(
                url=f"{frontend_url}?auth_error=user_profile_fetch_failed",
                status_code=status.HTTP_302_FOUND,
            )

        user_data = user_response.json()
        login = user_data.get("login")
        if not login:
            logger.error("User profile response missing login field.")
            return RedirectResponse(
                url=f"{frontend_url}?auth_error=invalid_user_data",
                status_code=status.HTTP_302_FOUND,
            )

        # Store user profile and backend access token in HTTP-only session cookie
        request.session["access_token"] = access_token
        request.session["user"] = {
            "login": login,
            "name": user_data.get("name") or login,
            "avatar_url": user_data.get("avatar_url", ""),
        }

        return RedirectResponse(url=frontend_url, status_code=status.HTTP_302_FOUND)


    except Exception:
        logger.exception("Unexpected exception during GitHub OAuth callback processing.")
        return RedirectResponse(
            url=f"{frontend_url}?auth_error=internal_auth_error",
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/me")
def get_current_user(request: Request):
    """Return authenticated user profile or unauthenticated status."""
    user = request.session.get("user")
    if user and isinstance(user, dict) and user.get("login"):
        return {
            "authenticated": True,
            "login": user.get("login"),
            "name": user.get("name") or user.get("login"),
            "avatar_url": user.get("avatar_url", ""),
        }

    return {"authenticated": False}


@router.post("/logout")
def logout(request: Request):
    """Clear the session cookie and log out the user."""
    request.session.clear()
    return {"message": "Logged out successfully"}
