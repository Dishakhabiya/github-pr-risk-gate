from fastapi.testclient import TestClient
from app.api.main import app
from unittest.mock import patch, MagicMock
from app.rag.retrieval import PRInfo

client = TestClient(app)

def test_question_generation_endpoint_has_ids():
    mock_chunks = [{"metadata": {"file_path": "test.py"}, "content": "test content"}]
    
    with patch("app.rag.retrieval.PRRetriever.retrieve_context", return_value=mock_chunks):
        payload = {
            "repository": "test/repo",
            "title": "Test PR",
            "changed_files": ["test.py"]
        }
        response = client.post("/api/rag/pr/questions?num_questions=2", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) == 2
        
        # Verify question_id exists and is valid
        q1 = data["questions"][0]
        q2 = data["questions"][1]
        
        assert q1["question_id"] == "q1"
        assert q2["question_id"] == "q2"

def test_answer_submission_valid_id():
    pr_mock = {
        "title": "Test PR", "body": "Body", "pr_id": 123,
        "repository": "test/repo", "commits": [], "changed_files": [],
        "diff": "", "html_url": "https://github.com/test/repo/pull/123",
    }
    with patch("app.github.pr_service.GitHubPRService.fetch_pr_details", return_value=pr_mock), \
         patch("app.github.client.GitHubClient.post_issue_comment", return_value={}):
        payload = {
            "repository": "test/repo",
            "pr_number": 123,
            "answers": [
                {
                    "question_id": "q1",
                    "question": "What is this?",
                    "category": "tests",
                    "answer": "This is a substantial test answer demonstrating understanding.",
                }
            ],
        }
        response = client.post("/api/rag/questions/answers", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "decision" in data
        assert "understanding_score" in data
        assert "risk_score" in data

def test_answer_submission_missing_id():
    payload = {
        "repository": "test/repo",
        "pr_number": 123,
        "answers": [
            {
                "question": "What is this?",
                "category": "tests",
                "answer": "This is a test."
            }
        ]
    }
    response = client.post("/api/rag/questions/answers", json=payload)
    # Should fail validation because question_id is now required
    assert response.status_code == 422
    assert "question_id" in response.text


def test_question_generation_session_token():
    """Test that get_github_client extracts access_token from session when available."""
    from app.api.rag_routes import get_github_client
    mock_request = MagicMock()
    mock_request.session = {"access_token": "gho_test_oauth_token"}

    client_obj = get_github_client(mock_request)
    assert client_obj.token == "gho_test_oauth_token"
