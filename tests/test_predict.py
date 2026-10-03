from unittest.mock import MagicMock, patch
import pytest

from ml.predict import PRRiskPredictor, predict_pr_risk


@pytest.fixture
def sample_pr_and_diff():
    pr_data = {
        "pr_id": 999,
        "title": "Fix critical race condition in server",
        "body": "Fixes #123",
        "commits": [{"sha": "abc"}],
        "changed_files": [
            {"filename": "app/server.py", "status": "modified", "additions": 45, "deletions": 5, "changes": 50}
        ],
        "diff": "diff --git a/app/server.py b/app/server.py\n--- a/app/server.py\n+++ b/app/server.py\n@@ -1,1 +1,1 @@\n-old\n+new",
    }
    diff_data = {
        "files_changed": ["app/server.py"],
        "added_lines": ["+new"],
        "deleted_lines": ["-old"],
        "num_added_lines": 45,
        "num_deleted_lines": 5,
        "binary_files": [],
    }
    return pr_data, diff_data


def test_successful_model_loading():
    predictor = PRRiskPredictor(model_path="artifacts/risk_model.joblib")
    pipeline = predictor.load_model()
    assert pipeline is not None
    assert pipeline.is_trained is True


def test_valid_prediction(sample_pr_and_diff):
    pr_data, diff_data = sample_pr_and_diff
    result = predict_pr_risk(pr_data, diff_data, model_path="artifacts/risk_model.joblib", threshold=0.5)

    assert result["pr_id"] == 999
    assert "risk_score" in result
    assert "risk_level" in result
    assert result["threshold"] == 0.5
    assert result["risk_level"] in ("HIGH", "LOW")
    assert isinstance(result["risk_score"], float)


def test_risk_score_range(sample_pr_and_diff):
    pr_data, diff_data = sample_pr_and_diff
    result = predict_pr_risk(pr_data, diff_data)

    score = result["risk_score"]
    assert 0.0 <= score <= 1.0


def test_threshold_behavior(sample_pr_and_diff):
    pr_data, diff_data = sample_pr_and_diff

    # Low threshold forces HIGH
    res_low_thresh = predict_pr_risk(pr_data, diff_data, threshold=0.0)
    assert res_low_thresh["risk_level"] == "HIGH"

    # High threshold forces LOW
    res_high_thresh = predict_pr_risk(pr_data, diff_data, threshold=1.01)
    assert res_high_thresh["risk_level"] == "LOW"


def test_missing_model_artifact():
    predictor = PRRiskPredictor(model_path="artifacts/non_existent_model.joblib")
    with pytest.raises(FileNotFoundError) as exc_info:
        predictor.load_model()
    assert "not found" in str(exc_info.value).lower()


def test_no_post_creation_outcome_fields_allowed():
    predictor = PRRiskPredictor(model_path="artifacts/risk_model.joblib")
    forbidden_features = {
        "files_changed": 2,
        "lines_added": 20,
        "review_comments_count": 10,  # Forbidden post-creation field!
    }
    with pytest.raises(ValueError) as exc_info:
        predictor.predict_from_features(forbidden_features)
    assert "DATA LEAKAGE ERROR" in str(exc_info.value)


def test_no_retraining_during_prediction(sample_pr_and_diff):
    pr_data, diff_data = sample_pr_and_diff
    predictor = PRRiskPredictor(model_path="artifacts/risk_model.joblib")

    pipeline = predictor.load_model()

    # Verify fit and train methods on model and preprocessor are NOT called during prediction
    with patch.object(pipeline.model, "fit", side_effect=AssertionError("Model.fit must NOT be called during prediction")):
        with patch.object(pipeline.preprocessor, "fit_transform", side_effect=AssertionError("Preprocessor.fit_transform must NOT be called during prediction")):
            result = predictor.predict_pr_risk(pr_data, diff_data)

    assert result["pr_id"] == 999
    assert 0.0 <= result["risk_score"] <= 1.0
