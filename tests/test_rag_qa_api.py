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
    payload = {
        "repository": "test/repo",
        "pr_number": 123,
        "answers": [
            {
                "question_id": "q1",
                "question": "What is this?",
                "category": "tests",
                "answer": "This is a test."
            }
        ]
    }
    response = client.post("/api/rag/questions/answers", json=payload)
    assert response.status_code == 200
    assert response.json()["submitted_answers_count"] == 1

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
