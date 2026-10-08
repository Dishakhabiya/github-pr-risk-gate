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

from app.api.schemas import EvaluationDecisionResponse
from app.rag.evaluation import Evaluator, DecisionEngine
from ml.predict import predict_pr_risk
from app.preprocessing.diff_processor import preprocess_diff
from app.github.client import GitHubClient

@router.post("/rag/questions/answers", response_model=EvaluationDecisionResponse)
def submit_pr_answers(
    request: SubmitAnswersRequest,
    client: GitHubClient = Depends(get_github_client),
    vector_db: VectorDB = Depends(get_vector_db)
):
    """
    US-20: Integrate full answer evaluation, risk scoring, and PASS/BLOCK decision.
    """
    try:
        owner, repo = request.repository.split("/", 1)
        pr_number = request.pr_number
        
        # 1. Fetch PR details for Risk Score & Context Search
        from app.github.pr_service import fetch_pr_details
        pr_data = fetch_pr_details(owner, repo, pr_number, client=client)
        raw_diff = pr_data.get("diff", "")
        diff_data = preprocess_diff(raw_diff)
        
        # 2. Retrieve context chunks (RAG) BEFORE risk prediction so LLM can use them
        pr_info = PRInfo(
            repository=request.repository,
            title=pr_data.get("title", ""),
            description=pr_data.get("body", ""),
            changed_files=diff_data.get("files_changed", []),
            diff=raw_diff
        )
        retriever = PRRetriever(vector_db)
        context_chunks = retriever.retrieve_context(pr_info, top_k=5)
        
        # 3. Get ML Risk Prediction (Now enhanced with RAG context)
        risk_prediction = predict_pr_risk(pr_data, diff_data, context_chunks=context_chunks)
        risk_level = risk_prediction.get("risk_level", "LOW")
        risk_score = risk_prediction.get("risk_score", 0.0)
        
        # 4. Evaluate Answers (US-13 & US-14)
        answers_payload = [ans.dict() for ans in request.answers]
        evaluator = Evaluator()
        eval_result = evaluator.evaluate_all(answers_payload, context_chunks)
        understanding_score = eval_result.understanding_score
        
        # 5. Make PASS/BLOCK Decision (US-15)
        decision, reasons = DecisionEngine.make_decision(risk_level, understanding_score)
        
        # 6. Post GitHub Comment (US-16)
        # Format the comment as Markdown
        comment_body = f"## PR Risk Gate Analysis: **{decision}**\n\n"
        comment_body += f"**ML Risk Score:** {risk_score:.2f} ({risk_level})\n"
        comment_body += f"**Understanding Score:** {understanding_score:.2f}\n\n"
        comment_body += "### Reasons:\n"
        for r in reasons:
            comment_body += f"- {r}\n"
        
        comment_body += "\n### Answer Evaluation Summary:\n"
        for ev in eval_result.evaluations:
            status = "✅ Correct" if ev.correct else "❌ Needs Improvement"
            comment_body += f"- **Q{ev.question_id}:** {status} (Score: {ev.score:.2f}) - {ev.feedback}\n"
            
        try:
            client.post_issue_comment(owner, repo, pr_number, comment_body)
        except Exception as e:
            # We don't want to fail the whole process if commenting fails (e.g. in test envs)
            print(f"Warning: Failed to post GitHub comment: {e}")
            
        github_pr_url = pr_data.get("html_url", f"https://github.com/{owner}/{repo}/pull/{pr_number}")
        
        return EvaluationDecisionResponse(
            pr_id=pr_number,
            repository=request.repository,
            risk_score=risk_score,
            risk_level=risk_level,
            understanding_score=understanding_score,
            decision=decision,
            reasons=reasons,
            github_pr_url=github_pr_url
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
