import os
import sys
import logging
from app.github.client import GitHubClient
from app.preprocessing.diff_processor import preprocess_diff
from ml.predict import predict_pr_risk
from app.rag.retrieval import PRInfo, PRRetriever
from app.rag.vector_db import VectorDB
from app.rag.evaluation import Evaluator, DecisionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    repo_full = os.getenv("REPOSITORY")
    pr_number_str = os.getenv("PR_NUMBER")
    
    if not repo_full or not pr_number_str:
        logger.error("REPOSITORY or PR_NUMBER environment variables not set.")
        sys.exit(1)
        
    try:
        pr_number = int(pr_number_str)
        owner, repo = repo_full.split("/", 1)
    except ValueError:
        logger.error("Invalid REPOSITORY or PR_NUMBER format.")
        sys.exit(1)

    client = GitHubClient()
    vector_db = VectorDB()
    
    logger.info(f"Running automated analysis for {owner}/{repo}#{pr_number}")
    
    try:
        pr_data = client.get_pull_request(owner, repo, pr_number)
        raw_diff = client.get_pull_request_diff(owner, repo, pr_number)
        diff_data = preprocess_diff(raw_diff)
        
        risk_prediction = predict_pr_risk(pr_data, diff_data)
        risk_level = risk_prediction.get("risk_level", "LOW")
        risk_score = risk_prediction.get("risk_score", 0.0)
        
        pr_info = PRInfo(
            repository=repo_full,
            title=pr_data.get("title", ""),
            description=pr_data.get("body", ""),
            changed_files=diff_data.get("files_changed", []),
            diff=raw_diff
        )
        retriever = PRRetriever(vector_db)
        context_chunks = retriever.retrieve_context(pr_info, top_k=5)
        
        # Since this is automated and no developer answers are present,
        # we can pass an empty list which yields 0.0 understanding score
        # and defaults to BLOCK if risk is high, or PASS if risk is low.
        evaluator = Evaluator()
        eval_result = evaluator.evaluate_all([], context_chunks)
        understanding_score = eval_result.understanding_score
        
        decision, reasons = DecisionEngine.make_decision(risk_level, understanding_score)
        
        comment_body = f"## Automated PR Risk Gate Analysis: **{decision}**\n\n"
        comment_body += f"**ML Risk Score:** {risk_score:.2f} ({risk_level})\n"
        comment_body += f"**Understanding Score:** {understanding_score:.2f} (No developer answers submitted)\n\n"
        comment_body += "### Reasons:\n"
        for r in reasons:
            comment_body += f"- {r}\n"
            
        client.post_issue_comment(owner, repo, pr_number, comment_body)
        logger.info(f"Analysis complete. Decision: {decision}")
        
    except Exception as e:
        logger.error(f"Automated analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
