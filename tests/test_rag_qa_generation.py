import pytest
from app.rag.qa_generation import QuestionGenerator, PRQuestion
from app.rag.retrieval import PRInfo

def test_question_generation_from_pr_info():
    generator = QuestionGenerator()
    pr_info = PRInfo(
        repository="owner/repo",
        title="Fix bug in auth",
        changed_files=["app/auth.py", "tests/test_auth.py"]
    )
    
    questions = generator.generate_questions(pr_info, context_chunks=[], num_questions=3)
    
    assert len(questions) == 3
    # Check if edge cases question uses changed file
    assert any("app/auth.py" in q.question for q in questions)
    assert any(q.category == "edge cases" for q in questions)

def test_question_generation_with_context():
    generator = QuestionGenerator()
    pr_info = PRInfo(repository="owner/repo")
    
    context_chunks = [
        {
            "metadata": {"file_path": "app/db.py"},
            "content": "def connect_to_db():\n    pass"
        }
    ]
    
    questions = generator.generate_questions(pr_info, context_chunks=context_chunks, num_questions=1)
    
    assert len(questions) == 1
    # Check if context snippet is embedded
    assert "app/db.py" in questions[0].question
    assert "connect_to_db" in questions[0].question
    assert questions[0].supporting_context.startswith("def connect_to_db")
    assert questions[0].category == "impact on existing code"

def test_question_generation_configurable_count():
    generator = QuestionGenerator()
    pr_info = PRInfo(repository="owner/repo", changed_files=["a.py", "b.py", "c.py"])
    context_chunks = [{"metadata": {"file_path": "x.py"}, "content": "func()"}] * 5
    
    questions = generator.generate_questions(pr_info, context_chunks, num_questions=5)
    assert len(questions) == 5

def test_question_generation_missing_info_and_context():
    generator = QuestionGenerator()
    pr_info = PRInfo(repository="owner/repo")
    
    questions = generator.generate_questions(pr_info, context_chunks=[], num_questions=2)
    
    assert len(questions) == 2
    # Should fallback to generic questions if nothing is provided
    assert any("unit tests" in q.question.lower() for q in questions)
    assert all(q.category in ["tests", "maintainability", "correctness/logic"] for q in questions)
