import pytest
import os
import shutil
from app.rag.chunking import TextSplitter, Chunk
from app.rag.vector_db import VectorDB

def test_text_splitter():
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)
    doc = {
        "repository": "test/repo",
        "file_path": "test.py",
        "language": ".py",
        "content": "0123456789abcdefghij"
    }
    
    chunks = splitter.split_document(doc)
    # chunk 1: 0123456789
    # chunk 2: 89abcdefgh
    # chunk 3: ghij
    assert len(chunks) == 3
    assert chunks[0].content == "0123456789"
    assert chunks[1].content == "89abcdefgh"
    assert chunks[2].content == "ghij"
    
    # Check metadata
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[1].metadata["chunk_index"] == 1
    assert chunks[0].metadata["repository"] == "test/repo"

def test_text_splitter_empty_small():
    splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
    
    # Empty
    assert len(splitter.split_document({"content": ""})) == 0
    assert len(splitter.split_document({"content": "   \n  "})) == 0
    
    # Small
    chunks = splitter.split_document({
        "content": "small code",
        "repository": "r", "file_path": "f", "language": "l"
    })
    assert len(chunks) == 1
    assert chunks[0].content == "small code"

def test_vector_db_insertion_and_search():
    persist_dir = "tests/test_chroma_db"
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        
    db = VectorDB(persist_directory=persist_dir)
    
    chunk1 = Chunk("def hello_world():\n    print('hello world')", {"repository": "a/b", "file_path": "hello.py", "chunk_index": 0})
    chunk2 = Chunk("const x = 42;\nconsole.log(x);", {"repository": "a/b", "file_path": "main.js", "chunk_index": 0})
    chunk3 = Chunk("SELECT * FROM users WHERE age > 18;", {"repository": "a/b", "file_path": "query.sql", "chunk_index": 0})
    
    # Insert chunks. This should also trigger embeddings.
    db.add_chunks([chunk1, chunk2, chunk3])
    
    # Test Similarity Search
    results = db.search("SQL query for users", n_results=1)
    
    assert len(results) == 1
    assert "SELECT * FROM users" in results[0]["content"]
    assert results[0]["metadata"]["file_path"] == "query.sql"
    
    # Clean up
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

def test_vector_db_persistence():
    persist_dir = "tests/test_chroma_db_persist"
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        
    db1 = VectorDB(persist_directory=persist_dir)
    chunk = Chunk("persistent data here", {"repository": "persist/test", "file_path": "test.txt", "chunk_index": 0})
    db1.add_chunks([chunk])
    
    # Force deletion of db1 instance to simulate process exit
    del db1
    
    # Reload DB
    db2 = VectorDB(persist_directory=persist_dir)
    results = db2.search("persistent data", n_results=1)
    
    assert len(results) == 1
    assert results[0]["content"] == "persistent data here"
    
    # Clean up
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
