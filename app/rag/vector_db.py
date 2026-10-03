import os
import chromadb
from typing import List, Dict, Any
from app.rag.chunking import Chunk
import logging

logger = logging.getLogger(__name__)

class VectorDB:
    """Persistent Vector Database using ChromaDB for storing and retrieving code chunks."""
    
    def __init__(self, persist_directory: str = "artifacts/chroma_db"):
        # Ensure the directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize the persistent client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # We use the default embedding function (all-MiniLM-L6-v2 via ONNX runtime)
        # This fulfills the requirement for a free/local embedding model without OpenAI keys.
        self.collection = self.client.get_or_create_collection(
            name="repository_context"
        )
        logger.info(f"Initialized VectorDB at {persist_directory} with collection 'repository_context'")
        
    def add_chunks(self, chunks: List[Chunk]):
        """Embed and store a list of chunks in the vector database."""
        if not chunks:
            logger.warning("No chunks to add to VectorDB.")
            return
            
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            # Generate a unique ID based on repository, file_path, and chunk_index
            repo = chunk.metadata.get("repository", "unknown_repo")
            path = chunk.metadata.get("file_path", "unknown_path")
            idx = chunk.metadata.get("chunk_index", 0)
            
            # Sanitize ID to ensure it is valid
            chunk_id = f"{repo}::{path}::{idx}"
            
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(chunk.metadata)
            
        # Add to ChromaDB. It will automatically tokenize and embed using its embedding function.
        batch_size = 5000  # Chroma usually recommends batching if > 5000
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            self.collection.upsert(
                ids=ids[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
            logger.info(f"Upserted chunks {i} to {end_idx-1} into VectorDB.")

    def search(self, query_text: str, n_results: int = 5, where_filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Perform similarity search and return relevant chunks."""
        query_args = {
            "query_texts": [query_text],
            "n_results": n_results
        }
        if where_filter:
            query_args["where"] = where_filter
            
        results = self.collection.query(**query_args)
        
        formatted_results = []
        if not results or not results["documents"] or not results["documents"][0]:
            return formatted_results
            
        for i in range(len(results["documents"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if "distances" in results and results["distances"] else None
            })
            
        return formatted_results
