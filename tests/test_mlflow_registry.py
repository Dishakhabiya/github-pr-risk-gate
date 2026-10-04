"""
US-19: MLflow Model Registry tests.

Tests verify:
- model registration
- creation of a new model version
- retrieving/listing registered versions
- selecting a specific model version
- loading the selected version for prediction
- prediction still returning the same expected response structure
- behavior when the requested model version does not exist
"""
import os
import sys
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mlflow
from ml.model import RiskModelPipeline
from ml.predict import PRRiskPredictor, predict_pr_risk
from ml.preprocessing import prepare_feature_matrix, split_dataset
from ml.tracking import REGISTERED_MODEL_NAME, mlflow_run, log_and_register_model


@pytest.fixture
def tmp_mlflow_dir(tmp_path):
    """Provide a per-test isolated MLflow tracking directory."""
    tracking_dir = str(tmp_path / "mlruns_registry_test")
    os.makedirs(tracking_dir, exist_ok=True)
    return tracking_dir


@pytest.fixture
def sample_records():
    """Minimal dataset records."""
    records = []
    for i in range(1, 20):
        is_high = 1 if i % 2 == 0 else 0
        records.append({
            "repository": "owner/repo",
            "pr_id": i,
            "created_at": f"2026-10-01T{i % 24:02d}:00:00Z",
            "files_changed": i,
            "lines_added": i * 10,
            "lines_deleted": i * 2,
            "total_lines_changed": i * 12,
            "commits_count": 1,
            "additions_to_deletions_ratio": 5.0,
            "source_files_changed": i,
            "title_length": 20,
            "body_length": 100,
            "has_linked_issue": 1,
            "risk_label": is_high,
        })
    return records


@pytest.fixture
def trained_pipeline(sample_records):
    """Provide a trained pipeline."""
    train_recs, _ = split_dataset(sample_records, test_size=0.2, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    pipeline = RiskModelPipeline(model_name="TestLR")
    pipeline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)
    return pipeline


def test_model_registration_and_versioning(tmp_mlflow_dir, trained_pipeline, tmp_path):
    """Test model registration and creation of multiple versions."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        mlflow.set_tracking_uri(tmp_mlflow_dir)
        client = mlflow.tracking.MlflowClient()

        # Run 1: Create version 1
        with mlflow_run(run_name="run1"):
            log_and_register_model(trained_pipeline, str(tmp_path / "model1.joblib"))

        # Run 2: Create version 2
        with mlflow_run(run_name="run2"):
            log_and_register_model(trained_pipeline, str(tmp_path / "model2.joblib"))

        # Verify registry
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
        assert len(versions) == 2
        
        v_numbers = [int(v.version) for v in versions]
        assert 1 in v_numbers
        assert 2 in v_numbers


def test_retrieving_and_selecting_model_version(tmp_mlflow_dir, trained_pipeline, tmp_path):
    """Test loading specific versions for prediction."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        mlflow.set_tracking_uri(tmp_mlflow_dir)
        
        # Create a version
        with mlflow_run():
            log_and_register_model(trained_pipeline, str(tmp_path / "dummy.joblib"))
            
        # Select 'latest'
        predictor = PRRiskPredictor(model_path=f"models:/{REGISTERED_MODEL_NAME}/latest")
        model = predictor.load_model()
        assert isinstance(model, RiskModelPipeline)
        
        # Select specific version (version 1)
        predictor_v1 = PRRiskPredictor(model_path=f"models:/{REGISTERED_MODEL_NAME}/1")
        model_v1 = predictor_v1.load_model()
        assert isinstance(model_v1, RiskModelPipeline)


def test_prediction_returns_expected_structure(tmp_mlflow_dir, trained_pipeline, tmp_path):
    """Test that MLflow-loaded models return the same prediction output."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        mlflow.set_tracking_uri(tmp_mlflow_dir)
        
        with mlflow_run():
            log_and_register_model(trained_pipeline, str(tmp_path / "dummy.joblib"))
            
        pr_data = {"files_changed": 3, "commits": [{"sha": "abc"}], "title": "A"}
        diff_data = {"files_changed": ["a.py"], "added_lines": ["+1"]}
        
        # Default behavior (uses models:/pr-risk-model/latest)
        result = predict_pr_risk(pr_data, diff_data)
        
        assert "pr_id" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "threshold" in result
        assert "model_name" in result
        assert result["risk_level"] in ("LOW", "HIGH")


def test_nonexistent_model_version_fallback_or_error(tmp_mlflow_dir):
    """Test behavior when requested MLflow model does not exist."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        mlflow.set_tracking_uri(tmp_mlflow_dir)
        
        # Predictor configured with nonexistent MLflow model
        predictor = PRRiskPredictor(model_path="models:/nonexistent-model/latest")
        
        # Since it fails to load from MLflow, it will fallback to "artifacts/risk_model.joblib".
        # Because we haven't trained a local joblib artifact in this test, it should raise FileNotFoundError.
        with pytest.raises(FileNotFoundError, match="Trained risk model artifact not found"):
            predictor.load_model()
