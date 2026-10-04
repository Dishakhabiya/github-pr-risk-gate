import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.rag.retrieval import PRInfo

logger = logging.getLogger(__name__)

class PRQuestion(BaseModel):
    question_id: str
    question: str
    category: str
    related_file: Optional[str] = None
    supporting_context: Optional[str] = None

class QuestionGenerator:
    """
    Generates PR-specific questions based on PR information and retrieved repository context.
    Currently uses a heuristic/template-based approach to ensure fast, local execution without 
    external API keys or heavy local LLM dependencies. This can be swapped with a real LLM 
    backend in the future.
    """
    
    def generate_questions(self, pr_info: PRInfo, context_chunks: List[Dict[str, Any]], num_questions: int = 3) -> List[PRQuestion]:
        questions = []
        
        # 1. Edge cases based on changed files
        if pr_info.changed_files:
            for file_path in pr_info.changed_files[:2]:
                if len(questions) >= num_questions:
                    break
                questions.append(PRQuestion(
                    question_id=f"q{len(questions) + 1}",
                    question=f"What are the main edge cases considered for the changes introduced in `{file_path}`?",
                    category="edge cases",
                    related_file=file_path
                ))
                
        # 2. Impact on existing code based on retrieved context chunks
        if context_chunks:
            for chunk in context_chunks:
                if len(questions) >= num_questions:
                    break
                    
                file_path = chunk.get("metadata", {}).get("file_path", "unknown_file")
                content = chunk.get("content", "")
                
                # Extract a small snippet to make the question highly specific to the context
                snippet = content[:60].replace('\n', ' ').strip()
                if snippet:
                    questions.append(PRQuestion(
                        question_id=f"q{len(questions) + 1}",
                        question=f"How do the PR changes impact the existing logic in `{file_path}`, specifically around: '{snippet}...'?",
                        category="impact on existing code",
                        related_file=file_path,
                        supporting_context=content[:500]  # First 500 chars as supporting context
                    ))
                    
        # 3. Security/Performance based on PR Title / Diff
        if len(questions) < num_questions and pr_info.title:
            questions.append(PRQuestion(
                question_id=f"q{len(questions) + 1}",
                question=f"Does the implementation for '{pr_info.title}' handle invalid inputs securely and perform optimally?",
                category="security/performance"
            ))
            
        # 4. Tests and maintainability (Fallback or if more questions needed)
        fallback_templates = [
            ("tests", "Are there sufficient unit tests and documentation covering these changes?"),
            ("maintainability", "Does the pull request adhere to architectural guidelines and maintain code readability?"),
            ("correctness/logic", "Does the proposed change preserve backward compatibility and logical correctness?"),
        ]
        fallback_idx = 0
        while len(questions) < num_questions:
            cat, q_text = fallback_templates[fallback_idx % len(fallback_templates)]
            questions.append(PRQuestion(
                question_id=f"q{len(questions) + 1}",
                question=q_text,
                category=cat
            ))
            fallback_idx += 1
            
        return questions[:num_questions]
