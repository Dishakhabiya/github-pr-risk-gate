import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.rag.vector_db import VectorDB

logger = logging.getLogger(__name__)

class PRInfo(BaseModel):
    repository: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    changed_files: Optional[List[str]] = []
    diff: Optional[str] = ""

class PRRetriever:
    """Retrieves relevant repository context for a Pull Request."""
    
    def __init__(self, vector_db: VectorDB):
        self.vector_db = vector_db
        
    def _build_query(self, pr_info: PRInfo) -> str:
        """Converts PR information into a semantic search query string."""
        query_parts = []
        
        if pr_info.title:
            query_parts.append(f"PR Title: {pr_info.title}")
            
        if pr_info.description:
            # We take only a snippet if it's extremely long to avoid maxing out context window
            desc = pr_info.description[:1000] if len(pr_info.description) > 1000 else pr_info.description
            query_parts.append(f"PR Description: {desc}")
            
        if pr_info.changed_files:
            files_str = ", ".join(pr_info.changed_files[:20]) # Limit to 20 files
            query_parts.append(f"Changed Files: {files_str}")
            
        if pr_info.diff:
            # Add a small snippet of the diff as context
            diff_snippet = pr_info.diff[:1000] if len(pr_info.diff) > 1000 else pr_info.diff
            query_parts.append(f"Code Changes:\n{diff_snippet}")
            
        if not query_parts:
            # Fallback if PR info is completely empty
            return "general repository context"
            
        return "\n".join(query_parts)

    def retrieve_context(self, pr_info: PRInfo, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant code chunks for the given PR.
        """
        if not pr_info.repository:
            logger.error("Cannot retrieve context: PR info is missing the 'repository' field.")
            return []
            
        query_text = self._build_query(pr_info)
        logger.info(f"Retrieving top {top_k} chunks for PR in {pr_info.repository} with query length {len(query_text)}")
        
        where_filter = {"repository": pr_info.repository}
        
        # Execute the search against VectorDB
        raw_results = self.vector_db.search(
            query_text=query_text,
            n_results=top_k,
            where_filter=where_filter
        )
        
        # Format the output clearly for downstream LLM prompt usage (US-11)
        # It's already mostly formatted by vector_db, but we deduplicate just in case 
        # (Chroma usually handles dupes based on ID, but we want to ensure clean output).
        seen_ids = set()
        clean_results = []
        
        for res in raw_results:
            chunk_id = res.get("id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                clean_results.append({
                    "id": chunk_id,
                    "content": res.get("content"),
                    "metadata": res.get("metadata", {}),
                    "relevance_distance": res.get("distance")
                })
                
        return clean_results
