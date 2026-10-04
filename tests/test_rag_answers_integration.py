from fastapi.testclient import TestClient
from app.api.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

# Mock fetch_pr_details (the correct call path after the rag_routes fix)
# and predict_pr_risk, retriever, evaluator, and comment poster.
@patch("app.github.pr_service.GitHubPRService.fetch_pr_details")
@patch("app.api.rag_routes.predict_pr_risk")
@patch("app.rag.retrieval.PRRetriever.retrieve_context")
@patch("app.rag.evaluation.Evaluator.evaluate_all")
@patch("app.github.client.GitHubClient.post_issue_comment")
def test_submit_pr_answers_end_to_end(
    mock_post_comment,
    mock_evaluate_all,
    mock_retrieve,
    mock_predict,
    mock_fetch_pr,
):
    # fetch_pr_details returns structured dict (commits as list, changed_files as list of dicts)
    mock_fetch_pr.return_value = {
        "title": "Test PR",
        "body": "Body",
        "pr_id": 123,
        "repository": "test/repo",
        "commits": [{"sha": "abc", "message": "msg", "author": "x", "date": "2024"}],
        "changed_files": [{"filename": "file.py", "status": "modified", "additions": 1, "deletions": 0, "changes": 1}],
        "diff": "diff --git a/file.py b/file.py\n+added",
        "html_url": "https://github.com/test/repo/pull/123",
    }
    mock_predict.return_value = {"risk_level": "LOW", "risk_score": 0.2}
    mock_retrieve.return_value = []

    from app.rag.evaluation import EvaluationResult, AnswerEvaluation
    mock_evaluate_all.return_value = EvaluationResult(
        evaluations=[AnswerEvaluation(question_id="1", score=1.0, correct=True, feedback="Good", reason="Good")],
        understanding_score=1.0,
        has_understood=True,
    )

    payload = {
        "repository": "test/repo",
        "pr_number": 123,
        "answers": [
            {
                "question_id": "1",
                "question": "What is this?",
                "category": "tests",
                "answer": "This is a test answer with enough detail.",
            }
        ],
    }

    response = client.post("/api/rag/questions/answers", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["decision"] == "PASS"
    assert data["understanding_score"] == 1.0
    assert data["risk_score"] == 0.2
    mock_post_comment.assert_called_once()


def test_submit_pr_answers_commits_as_int_regression():
    """
    Regression test: extract_features must not crash when 'commits' in pr_data
    is an integer (as returned by raw GitHub PR API) instead of a list.
    This was the root cause of 'int object is not iterable' in browser testing.
    """
    from app.features.extractor import extract_features
    from app.preprocessing.diff_processor import preprocess_diff

    # Simulate raw GitHub API pr_data where commits is an int (commit count)
    pr_data_raw_github = {
        "title": "Fix auth bug",
        "body": "Fixes issue #42",
        "commits": 5,          # <-- int, as GitHub raw API returns it
        "changed_files": [],   # GitHub raw API uses a different key; service normalizes it
        "number": 37,
    }
    diff_data = preprocess_diff("diff --git a/file.py b/file.py\n+new line")

    # This must NOT raise TypeError: 'int' object is not iterable
    features = extract_features(pr_data_raw_github, diff_data)
    assert features["commits_count"] == 5  # should use the int directly
