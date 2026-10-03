import base64
import logging
from typing import Any, Dict, List, Optional

from app.github.client import GitHubClient

logger = logging.getLogger(__name__)

# Constants for filtering
MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "generated",
    "vendor",
    "venv",
    ".venv",
    "__pycache__",
    ".idea",
    ".vscode",
}

EXCLUDED_EXTENSIONS = {
    # Images/Media
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".mp4", ".mp3", ".wav",
    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z", ".tgz",
    # Binaries/Compiled
    ".exe", ".dll", ".so", ".class", ".jar", ".pyc", ".pyo", ".pyd", ".o", ".obj",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Data/DB
    ".sqlite", ".db", ".sqlite3",
}

EXCLUDED_FILES = {
    ".env",
    ".env.example",
    ".env.local",
    "package-lock.json",
    "yarn.lock",
}

class RepositoryIngestor:
    """Service to fetch and prepare repository source files for RAG."""

    def __init__(self, github_client: GitHubClient):
        self.github_client = github_client

    def should_include_file(self, path: str, size: int) -> bool:
        """Determine if a file should be included based on path and size."""
        # Check size
        if size > MAX_FILE_SIZE_BYTES:
            return False

        path_parts = path.split("/")
        filename = path_parts[-1]
        
        # Check excluded directories
        for part in path_parts[:-1]:
            if part in EXCLUDED_DIRS:
                return False
                
        # Check exact filenames
        if filename in EXCLUDED_FILES:
            return False
            
        # Check extensions
        import os
        _, ext = os.path.splitext(filename)
        if ext.lower() in EXCLUDED_EXTENSIONS:
            return False
            
        return True

    def ingest_repository(
        self, owner: str, repo: str, branch: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch repository files and return them as prepared documents.
        """
        repo_full_name = f"{owner}/{repo}"
        logger.info(f"Starting ingestion for repository: {repo_full_name}")

        # Resolve branch if not provided
        if not branch:
            repo_info = self.github_client.get_repository(owner, repo)
            branch = repo_info.get("default_branch", "main")
            
        logger.info(f"Using branch: {branch}")

        # Fetch repository tree recursively
        tree_data = self.github_client.get_repository_tree(owner, repo, tree_sha=branch, recursive=True)
        tree = tree_data.get("tree", [])
        
        documents = []
        import os
        
        for item in tree:
            # We only care about files (blob)
            if item.get("type") != "blob":
                continue
                
            path = item.get("path", "")
            size = item.get("size", 0)
            
            if not self.should_include_file(path, size):
                continue
                
            try:
                # Fetch content
                file_data = self.github_client.get_file_content(owner, repo, path, ref=branch)
                content = ""
                if "content" in file_data:
                    # Content is usually base64 encoded
                    encoding = file_data.get("encoding", "")
                    if encoding == "base64":
                        try:
                            content = base64.b64decode(file_data["content"]).decode("utf-8")
                        except UnicodeDecodeError:
                            # Might be binary despite passing extension checks
                            logger.warning(f"Could not decode content of {path} as UTF-8. Skipping.")
                            continue
                    else:
                        content = file_data["content"]
                        
                _, ext = os.path.splitext(path)
                
                documents.append({
                    "repository": repo_full_name,
                    "file_path": path,
                    "content": content,
                    "language": ext.lower() if ext else "unknown"
                })
            except Exception as e:
                logger.error(f"Failed to fetch content for {path}: {str(e)}")
                
        logger.info(f"Ingestion completed. Retrieved {len(documents)} documents for {repo_full_name}.")
        return documents
