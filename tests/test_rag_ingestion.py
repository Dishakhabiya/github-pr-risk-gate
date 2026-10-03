import pytest
from unittest.mock import Mock, patch
from app.rag.ingestion import RepositoryIngestor
from app.github.exceptions import GitHubNotFoundError, GitHubAuthError

@pytest.fixture
def mock_github_client():
    client = Mock()
    client.get_repository.return_value = {"default_branch": "main"}
    return client

def test_should_include_file(mock_github_client):
    ingestor = RepositoryIngestor(mock_github_client)
    
    # Valid files
    assert ingestor.should_include_file("src/main.py", 1000) is True
    assert ingestor.should_include_file("README.md", 2000) is True
    
    # Excluded dirs
    assert ingestor.should_include_file("node_modules/package/index.js", 1000) is False
    assert ingestor.should_include_file(".git/config", 100) is False
    assert ingestor.should_include_file("build/output.js", 500) is False
    
    # Excluded files
    assert ingestor.should_include_file(".env", 100) is False
    assert ingestor.should_include_file("src/.env.example", 100) is False
    
    # Excluded extensions
    assert ingestor.should_include_file("logo.png", 5000) is False
    assert ingestor.should_include_file("app.exe", 5000) is False
    
    # Large files
    assert ingestor.should_include_file("big_data.csv", 600 * 1024) is False

def test_ingest_repository_success(mock_github_client):
    mock_github_client.get_repository_tree.return_value = {
        "tree": [
            {"type": "blob", "path": "main.py", "size": 100},
            {"type": "blob", "path": "utils.py", "size": 200},
            # Should be filtered out
            {"type": "blob", "path": "node_modules/test.js", "size": 100},
            {"type": "blob", "path": "image.png", "size": 1000},
        ]
    }
    
    import base64
    def mock_get_file_content(owner, repo, path, ref):
        content = f"content of {path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        return {"content": encoded, "encoding": "base64"}
        
    mock_github_client.get_file_content.side_effect = mock_get_file_content
    
    ingestor = RepositoryIngestor(mock_github_client)
    docs = ingestor.ingest_repository("test-owner", "test-repo")
    
    assert len(docs) == 2
    
    paths = [d["file_path"] for d in docs]
    assert "main.py" in paths
    assert "utils.py" in paths
    
    for doc in docs:
        assert doc["repository"] == "test-owner/test-repo"
        assert doc["language"] == ".py"
        assert "content of" in doc["content"]

def test_ingest_repository_binary_decode_error(mock_github_client):
    mock_github_client.get_repository_tree.return_value = {
        "tree": [
            {"type": "blob", "path": "bad_file.txt", "size": 100},
        ]
    }
    
    import base64
    def mock_get_file_content(owner, repo, path, ref):
        # Invalid utf-8 bytes
        bad_bytes = b'\xff\xfe\x00\x00'
        encoded = base64.b64encode(bad_bytes).decode("utf-8")
        return {"content": encoded, "encoding": "base64"}
        
    mock_github_client.get_file_content.side_effect = mock_get_file_content
    
    ingestor = RepositoryIngestor(mock_github_client)
    docs = ingestor.ingest_repository("test-owner", "test-repo")
    
    # Should skip the file that fails to decode
    assert len(docs) == 0

def test_ingest_repository_not_found(mock_github_client):
    mock_github_client.get_repository.side_effect = GitHubNotFoundError("Not found")
    ingestor = RepositoryIngestor(mock_github_client)
    
    with pytest.raises(GitHubNotFoundError):
        ingestor.ingest_repository("invalid-owner", "invalid-repo")

def test_ingest_repository_auth_error(mock_github_client):
    mock_github_client.get_repository.side_effect = GitHubAuthError("Auth failed")
    ingestor = RepositoryIngestor(mock_github_client)
    
    with pytest.raises(GitHubAuthError):
        ingestor.ingest_repository("owner", "repo")

def test_ingest_repository_empty_response(mock_github_client):
    mock_github_client.get_repository_tree.return_value = {"tree": []}
    ingestor = RepositoryIngestor(mock_github_client)
    
    docs = ingestor.ingest_repository("owner", "repo")
    assert len(docs) == 0
