from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from app.api.main import app
from app.github.exceptions import GitHubAuthError, GitHubNotFoundError

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_pr_endpoint_success():
    mock_pr_details = {
        "pr_id": 142645,
        "repository": "kubernetes/kubernetes",
        "title": "Refactor token auth",
        "body": "Fixes #99881",
        "diff": "diff --git a/file1.go b/file1.go\n+new line",
    }
    mock_diff_data = {
        "files_changed": ["file1.go"],
        "num_added_lines": 417,
        "num_deleted_lines": 9,
    }
    mock_features = {
        "files_changed": 1,
        "lines_added": 417,
        "lines_deleted": 9,
        "total_lines_changed": 426,
        "commits_count": 1,
    }
    mock_risk = {
        "pr_id": 142645,
        "risk_score": 0.1636,
        "risk_level": "LOW",
        "threshold": 0.5,
        "model_name": "Logistic Regression",
    }

    with patch("app.api.routes.fetch_pr_details", return_value=mock_pr_details), \
         patch("app.api.routes.preprocess_diff", return_value=mock_diff_data), \
         patch("app.api.routes.extract_features", return_value=mock_features), \
         patch("app.api.routes.predict_pr_risk", return_value=mock_risk):

        payload = {"repository": "kubernetes/kubernetes", "pr_number": 142645}
        response = client.post("/api/pr/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "kubernetes/kubernetes"
        assert data["pr_number"] == 142645
        assert data["title"] == "Refactor token auth"
        assert data["files_changed"] == 1
        assert data["lines_added"] == 417
        assert data["lines_deleted"] == 9
        assert data["risk_score"] == 0.1636
        assert data["risk_level"] == "LOW"


def test_analyze_pr_endpoint_invalid_repo_format():
    payload = {"repository": "invalid_repo_name_without_slash", "pr_number": 123}
    response = client.post("/api/pr/analyze", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_analyze_pr_endpoint_not_found():
    with patch("app.api.routes.fetch_pr_details", side_effect=GitHubNotFoundError("PR not found")):
        payload = {"repository": "nonexistent/repo", "pr_number": 99999}
        response = client.post("/api/pr/analyze", json=payload)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_analyze_pr_endpoint_auth_error():
    with patch("app.api.routes.fetch_pr_details", side_effect=GitHubAuthError("Invalid token")):
        payload = {"repository": "kubernetes/kubernetes", "pr_number": 123}
        response = client.post("/api/pr/analyze", json=payload)
        assert response.status_code == 401
        assert "authentication failed" in response.json()["detail"].lower()


def test_analyze_commit_endpoint_success():
    """Test POST /api/commit/analyze endpoint with valid commit sha."""
    mock_commit_details = {
        "pr_id": "abc123d",
        "sha": "abc123def4567890",
        "short_sha": "abc123d",
        "repository": "octocat/Hello-World",
        "title": "Fix security vulnerability",
        "body": "Detailed explanation",
        "author": "octocat",
        "diff": "diff --git a/main.py b/main.py\n+import os",
    }
    mock_diff_data = {
        "files_changed": ["main.py"],
        "num_added_lines": 1,
        "num_deleted_lines": 0,
    }
    mock_features = {
        "files_changed": 1,
        "lines_added": 1,
        "lines_deleted": 0,
        "total_lines_changed": 1,
        "commits_count": 1,
    }
    mock_risk = {
        "pr_id": "abc123d",
        "risk_score": 0.05,
        "risk_level": "LOW",
        "threshold": 0.5,
        "model_name": "Logistic Regression",
    }

    with patch("app.api.routes.fetch_commit_details", return_value=mock_commit_details), \
         patch("app.api.routes.preprocess_diff", return_value=mock_diff_data), \
         patch("app.api.routes.extract_features", return_value=mock_features), \
         patch("app.api.routes.predict_pr_risk", return_value=mock_risk):

        payload = {"repository": "octocat/Hello-World", "commit_sha": "abc123def4567890"}
        response = client.post("/api/commit/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "octocat/Hello-World"
        assert data["commit_sha"] == "abc123def4567890"
        assert data["short_sha"] == "abc123d"
        assert data["commit_message"] == "Fix security vulnerability"
        assert data["author"] == "octocat"
        assert data["analysis_type"] == "Commit Risk Analysis"
        assert data["risk_level"] == "LOW"


def test_analyze_commit_endpoint_not_found():
    """Test POST /api/commit/analyze returns 404 for invalid commit."""
    with patch("app.api.routes.fetch_commit_details", side_effect=GitHubNotFoundError("Commit not found")):
        payload = {"repository": "octocat/Hello-World", "commit_sha": "invalid_commit_sha_xyz"}
        response = client.post("/api/commit/analyze", json=payload)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_analyze_commit_endpoint_invalid_format():
    """Test POST /api/commit/analyze with empty commit SHA or repo."""
    payload = {"repository": "octocat/Hello-World", "commit_sha": "   "}
    response = client.post("/api/commit/analyze", json=payload)
    assert response.status_code == 422

