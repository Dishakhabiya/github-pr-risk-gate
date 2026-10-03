"""Custom exceptions for GitHub API interaction."""


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    pass


class GitHubAuthError(GitHubAPIError):
    """Raised when authentication fails or token is missing/invalid."""

    pass


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a repository or PR is not found."""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    pass
