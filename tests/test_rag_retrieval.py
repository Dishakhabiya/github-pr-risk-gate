import pytest
from app.rag.chunking import Chunk
from app.rag.vector_db import VectorDB
from app.rag.retrieval import PRRetriever, PRInfo
import os

@pytest.fixture(scope="module")
def setup_vector_db():
    db_path = "artifacts/chroma_db_test_retrieval"
    vector_db = VectorDB(persist_directory=db_path)
    
    # Pre-populate with some chunks for "owner/repo"
    chunks = [
        Chunk(
            content="def calculate_risk(pr):\n    return 'high'",
            metadata={"repository": "owner/repo", "file_path": "risk.py", "language": "python", "chunk_index": 0}
        ),
        Chunk(
            content="import os\ndef test_risk():\n    assert calculate_risk(None) == 'high'",
            metadata={"repository": "owner/repo", "file_path": "test_risk.py", "language": "python", "chunk_index": 0}
        ),
        Chunk(
            content="def unrelated_function():\n    pass",
            metadata={"repository": "other/repo", "file_path": "other.py", "language": "python", "chunk_index": 0}
        ),
        Chunk(
            content="def setup_database():\n    connect()",
            metadata={"repository": "owner/repo", "file_path": "db.py", "language": "python", "chunk_index": 0}
        )
    ]
    
    vector_db.add_chunks(chunks)
    
    yield vector_db
    
    # Cleanup (optional but good practice for persistent local DB in tests)
    # Chroma handles persistence via sqlite, deleting it recursively might be complex 
    # but for local tests it's okay to just leave it in artifacts or manually delete.

def test_pr_aware_retrieval_title_desc(setup_vector_db):
    retriever = PRRetriever(setup_vector_db)
    
    pr_info = PRInfo(
        repository="owner/repo",
        title="Fix risk calculation logic",
        description="This PR modifies the calculate_risk function to be more accurate."
    )
    
    results = retriever.retrieve_context(pr_info, top_k=2)
    
    assert len(results) <= 2
    assert any("calculate_risk" in res["content"] for res in results)
    # Should only return chunks from "owner/repo"
    assert all(res["metadata"]["repository"] == "owner/repo" for res in results)

def test_pr_aware_retrieval_changed_files(setup_vector_db):
    retriever = PRRetriever(setup_vector_db)
    
    pr_info = PRInfo(
        repository="owner/repo",
        changed_files=["db.py"]
    )
    
    results = retriever.retrieve_context(pr_info, top_k=1)
    
    assert len(results) == 1
    assert "setup_database" in results[0]["content"]

def test_pr_retrieval_top_k(setup_vector_db):
    retriever = PRRetriever(setup_vector_db)
    
    pr_info = PRInfo(
        repository="owner/repo",
        title="Update everything",
    )
    
    results = retriever.retrieve_context(pr_info, top_k=10)
    
    # Even with top_k=10, we only added 3 chunks for this repo
    assert len(results) <= 3
    # Check deduplication - IDs should be unique
    ids = [res["id"] for res in results]
    assert len(ids) == len(set(ids))

def test_pr_retrieval_missing_repo(setup_vector_db):
    retriever = PRRetriever(setup_vector_db)
    
    pr_info = PRInfo(
        repository="",
        title="Missing repo"
    )
    
    results = retriever.retrieve_context(pr_info)
    assert len(results) == 0

def test_pr_retrieval_empty_info(setup_vector_db):
    retriever = PRRetriever(setup_vector_db)
    
    # Should fall back to "general repository context" query
    pr_info = PRInfo(
        repository="owner/repo"
    )
    
    results = retriever.retrieve_context(pr_info, top_k=2)
    assert len(results) > 0
