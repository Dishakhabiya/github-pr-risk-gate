import logging
import os
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request, status
import requests

from app.github.client import GitHubClient
from app.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["GitHub Integration"])


def _get_headers_and_client(request: Request) -> tuple[Dict[str, str], str]:
    """Helper to retrieve headers for GitHub API request.
    
    Uses user's OAuth access_token from HTTP-only session if available,
    otherwise falls back to server-side GITHUB_TOKEN via GitHubClient.
    """
    user = request.session.get("user")
    if not user or not isinstance(user, dict) or not user.get("login"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access user repositories.",
        )

    access_token = request.session.get("access_token")
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-pr-risk-gate",
        }
    else:
        # Fallback to server-side GITHUB_TOKEN
        github_token = os.getenv("GITHUB_TOKEN", "")
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-pr-risk-gate",
        }

    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    return headers, api_url


@router.get("/repos", response_model=List[Dict[str, Any]])
def get_user_repositories(request: Request) -> List[Dict[str, Any]]:
    """Fetch repositories accessible to the authenticated GitHub user."""
    headers, api_url = _get_headers_and_client(request)

    # 1. Try fetching authenticated user repositories via /user/repos
    url = f"{api_url}/user/repos?sort=updated&per_page=100&type=all"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub authentication failed or access token expired.",
            )

        if not response.ok:
            # Fallback to public repos for user login if /user/repos is forbidden
            user = request.session.get("user", {})
            login = user.get("login", "")
            if login:
                url_fallback = f"{api_url}/users/{login}/repos?sort=updated&per_page=100"
                response = requests.get(url_fallback, headers=headers, timeout=10)

        if not response.ok:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching repositories: {response.status_code}",
            )

        raw_repos = response.json()
        if not isinstance(raw_repos, list):
            raw_repos = []

        repos = []
        for r in raw_repos:
            owner_obj = r.get("owner", {})
            repos.append({
                "full_name": r.get("full_name", ""),
                "name": r.get("name", ""),
                "owner": {"login": owner_obj.get("login", "")},
                "private": r.get("private", False),
                "html_url": r.get("html_url", ""),
            })

        return repos

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching user repositories.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user repositories from GitHub.",
        )


@router.get("/repos/{owner}/{repo}/pulls", response_model=List[Dict[str, Any]])
def get_repository_pull_requests(
    owner: str, repo: str, request: Request
) -> List[Dict[str, Any]]:
    """Fetch pull requests for a specific repository."""
    headers, api_url = _get_headers_and_client(request)

    url = f"{api_url}/repos/{owner}/{repo}/pulls?state=all&per_page=50&sort=updated&direction=desc"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found.",
            )
        if response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub authentication failed or access token expired.",
            )
        if not response.ok:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching pull requests: {response.status_code}",
            )

        raw_pulls = response.json()
        if not isinstance(raw_pulls, list):
            raw_pulls = []

        pulls = []
        for p in raw_pulls:
            user_obj = p.get("user", {})
            pulls.append({
                "number": p.get("number"),
                "title": p.get("title", ""),
                "state": p.get("state", "open"),
                "user": {"login": user_obj.get("login", "")},
                "html_url": p.get("html_url", ""),
                "created_at": p.get("created_at", ""),
                "updated_at": p.get("updated_at", ""),
            })

        return pulls

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching pull requests for %s/%s", owner, repo)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pull requests for repository {owner}/{repo}.",
        )


@router.get("/repos/{owner}/{repo}/commits", response_model=List[Dict[str, Any]])
def get_repository_commits(
    owner: str, repo: str, request: Request, per_page: int = 30
) -> List[Dict[str, Any]]:
    """Fetch recent commits for a repository."""
    headers, api_url = _get_headers_and_client(request)

    url = f"{api_url}/repos/{owner}/{repo}/commits?per_page={per_page}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found.",
            )
        if response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub authentication failed or access token expired.",
            )
        if not response.ok:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching commits: {response.status_code}",
            )

        raw_commits = response.json()
        if not isinstance(raw_commits, list):
            raw_commits = []

        commits = []
        for c in raw_commits:
            sha = c.get("sha", "")
            commit_obj = c.get("commit", {})
            author_obj = c.get("author") or commit_obj.get("author") or {}
            message = commit_obj.get("message", "")
            first_line_message = message.split("\n")[0] if message else ""

            commits.append({
                "sha": sha,
                "short_sha": sha[:7] if sha else "",
                "message": first_line_message,
                "full_message": message,
                "author": {
                    "login": author_obj.get("login") or author_obj.get("name") or "unknown",
                    "name": commit_obj.get("author", {}).get("name") or "",
                },
                "date": commit_obj.get("author", {}).get("date") or "",
                "html_url": c.get("html_url", ""),
            })

        return commits

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching commits for %s/%s", owner, repo)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve commits for repository {owner}/{repo}.",
        )

