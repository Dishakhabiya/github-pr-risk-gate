from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class Chunk:
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata

    def to_dict(self):
        return {
            "content": self.content,
            "metadata": self.metadata
        }

class TextSplitter:
    """Splits source code documents into smaller chunks for embeddings."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(self, document: Dict[str, Any]) -> List[Chunk]:
        """Split a single document into multiple chunks."""
        text = document.get("content", "")
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            # Try to snap to the last newline if we are not at the end of the text
            if end < text_length:
                last_newline = text.rfind('\n', start, end)
                # Only snap if the newline is reasonably far along
                if last_newline != -1 and (last_newline - start) > (self.chunk_size // 2):
                    end = last_newline + 1

            chunk_content = text[start:end].strip()
            if chunk_content:
                metadata = {
                    "repository": document.get("repository", "unknown"),
                    "file_path": document.get("file_path", "unknown"),
                    "language": document.get("language", "unknown"),
                    "chunk_index": chunk_index
                }
                chunks.append(Chunk(content=chunk_content, metadata=metadata))
                chunk_index += 1

            if end == text_length:
                break
                
            start = end - self.chunk_overlap

        return chunks

    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Chunk]:
        """Split a list of documents into chunks."""
        all_chunks = []
        for doc in documents:
            all_chunks.extend(self.split_document(doc))
        return all_chunks
