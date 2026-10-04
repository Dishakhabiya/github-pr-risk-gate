from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List, Dict
from app.github.client import GitHubClient
from app.github.exceptions import GitHubAPIError, GitHubAuthError, GitHubNotFoundError
from app.rag.ingestion import RepositoryIngestor
from app.rag.chunking import TextSplitter
from app.rag.vector_db import VectorDB
from pydantic import BaseModel

router = APIRouter()

class IngestRequest(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None

def get_github_client(request: Request) -> GitHubClient:
    access_token = request.session.get("access_token") if hasattr(request, "session") and request.session else None
    return GitHubClient(token=access_token)

@router.post("/rag/repository/ingest")
def ingest_repository(request: IngestRequest, client: GitHubClient = Depends(get_github_client)):
    """
    Ingest a GitHub repository to prepare it for RAG.
    """
    ingestor = RepositoryIngestor(client)
    try:
        documents = ingestor.ingest_repository(
            owner=request.owner,
            repo=request.repo,
            branch=request.branch
        )
        return {
            "status": "success",
            "message": f"Successfully ingested {len(documents)} documents.",
            "repository": f"{request.owner}/{request.repo}",
            "documents_count": len(documents)
        }
    except GitHubNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

def get_vector_db() -> VectorDB:
    return VectorDB()

@router.post("/rag/repository/index")
def index_repository(
    request: IngestRequest,
    client: GitHubClient = Depends(get_github_client),
    vector_db: VectorDB = Depends(get_vector_db)
):
    """
    Ingest, chunk, embed, and store a GitHub repository into the Vector DB.
    """
    ingestor = RepositoryIngestor(client)
    try:
        # Step 1: Ingest
        documents = ingestor.ingest_repository(
            owner=request.owner,
            repo=request.repo,
            branch=request.branch
        )
        
        # Step 2: Chunk
        splitter = TextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
        
        # Step 3: Embed and Store
        vector_db.add_chunks(chunks)
        
        return {
            "status": "success",
            "message": f"Successfully indexed repository.",
            "repository": f"{request.owner}/{request.repo}",
            "documents_count": len(documents),
            "chunks_stored": len(chunks)
        }
    except GitHubNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

from app.rag.retrieval import PRInfo, PRRetriever

@router.post("/rag/pr/retrieve")
def retrieve_pr_context(
    pr_info: PRInfo,
    top_k: int = 5,
    vector_db: VectorDB = Depends(get_vector_db)
):
    """
    Retrieve relevant repository context for a Pull Request.
    """
    retriever = PRRetriever(vector_db)
    
    try:
        chunks = retriever.retrieve_context(pr_info, top_k=top_k)
        return {
            "status": "success",
            "repository": pr_info.repository,
            "retrieved_chunks_count": len(chunks),
            "chunks": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

from app.rag.qa_generation import QuestionGenerator

@router.post("/rag/pr/questions")
def generate_pr_questions(
    pr_info: PRInfo,
    num_questions: int = 3,
    top_k_context: int = 5,
    vector_db: VectorDB = Depends(get_vector_db)
):
    """
    Generate PR-specific questions using PR info and retrieved repository context.
    """
    retriever = PRRetriever(vector_db)
    generator = QuestionGenerator()
    
    try:
        # Step 1: Retrieve context chunks
        context_chunks = retriever.retrieve_context(pr_info, top_k=top_k_context)
        
        # Step 2: Generate questions
        questions = generator.generate_questions(pr_info, context_chunks, num_questions=num_questions)
        
        return {
            "status": "success",
            "repository": pr_info.repository,
            "retrieved_chunks_count": len(context_chunks),
            "questions_count": len(questions),
            "questions": [q.dict() for q in questions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
class Answer(BaseModel):
    question_id: str
    question: str
    category: str
    answer: str

class SubmitAnswersRequest(BaseModel):
    repository: str
    pr_number: int
    answers: List[Answer]

@router.post("/rag/questions/answers")
def submit_pr_answers(request: SubmitAnswersRequest):
    """
    Submit developer answers to the generated PR questions.
    """
    # Simply echo back the answers with a success message for now.
    # In US-13, this will be consumed by the LLM evaluation.
    return {
        "status": "success",
        "message": "Answers submitted successfully.",
        "repository": request.repository,
        "pr_number": request.pr_number,
        "submitted_answers_count": len(request.answers)
    }
