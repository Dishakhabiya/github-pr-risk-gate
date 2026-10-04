from unittest.mock import patch, MagicMock
from app.rag.evaluation import Evaluator, DecisionEngine, AnswerEvaluation, EvaluationResult

def test_heuristic_evaluation_too_short():
    evaluator = Evaluator()
    result = evaluator._heuristic_evaluation("What is this?", "general", "fix", "q1")
    assert result.score == 0.2
    assert result.correct is False

def test_heuristic_evaluation_acceptable():
    evaluator = Evaluator()
    result = evaluator._heuristic_evaluation("What is this?", "general", "I handled the null pointer exception safely.", "q1")
    assert result.score == 0.8
    assert result.correct is True

def test_decision_engine_block_on_low_understanding():
    decision, reasons = DecisionEngine.make_decision("LOW", 0.3)
    assert decision == "BLOCK"
    assert "insufficient understanding" in reasons[0]

def test_decision_engine_block_on_high_risk_moderate_understanding():
    decision, reasons = DecisionEngine.make_decision("HIGH", 0.7)
    assert decision == "BLOCK"
    assert "High risk PR requires" in reasons[0]

def test_decision_engine_pass():
    decision, reasons = DecisionEngine.make_decision("LOW", 0.7)
    assert decision == "PASS"

def test_decision_engine_pass_high_risk():
    decision, reasons = DecisionEngine.make_decision("HIGH", 0.85)
    assert decision == "PASS"

@patch("app.rag.evaluation.openai.OpenAI")
def test_evaluate_answer_llm(mock_openai):
    # Setup mock
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 0.9, "correct": true, "feedback": "Good job.", "reason": "Accurate."}'
    mock_client.chat.completions.create.return_value = mock_response
    
    import os
    os.environ["OPENAI_API_KEY"] = "fake_key"
    
    evaluator = Evaluator()
    result = evaluator.evaluate_answer("Question", "cat", "Long answer", "context", "q1")
    
    assert result.score == 0.9
    assert result.correct is True
    assert result.question_id == "q1"
    
    os.environ.pop("OPENAI_API_KEY", None)
