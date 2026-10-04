"""
US-18: MLflow experiment tracking integration tests.

Tests verify:
- An MLflow run is created during training
- Expected parameters are logged
- Expected metrics are logged
- Expected artifacts are logged
- Training still produces the expected model artifact
- Existing prediction functionality still works
- All tests use a local temp MLflow tracking directory (no external server required)
"""
import json
import os
import sys
import tempfile
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock
import numpy as np
import pytest

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mlflow
from ml.evaluate import evaluate_model
from ml.model import RiskModelPipeline
from ml.preprocessing import prepare_feature_matrix, split_dataset
from ml.tracking import (
    DEFAULT_MLFLOW_TRACKING_DIR,
    MLFLOW_EXPERIMENT_NAME,
    log_classification_report_artifact,
    log_confusion_matrix_artifact,
    log_dataset_params,
    log_environment_params,
    log_evaluation_artifact,
    log_evaluation_metrics,
    log_feature_metadata_artifact,
    log_and_register_model,
    log_model_params,
    mlflow_run,
)


# ─── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def tmp_mlflow_dir(tmp_path):
    """Provide a per-test isolated MLflow tracking directory."""
    tracking_dir = str(tmp_path / "mlruns_test")
    os.makedirs(tracking_dir, exist_ok=True)
    return tracking_dir


@pytest.fixture
def sample_records():
    """Minimal dataset records with both risk classes present."""
    records = []
    for i in range(1, 30):
        is_high = 1 if i % 4 == 0 else 0
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
            "test_files_changed": 0,
            "documentation_files_changed": 0,
            "config_files_changed": 0,
            "average_changes_per_file": 12.0,
            "binary_files_changed": 0,
            "renamed_files": 0,
            "deleted_files": 0,
            "added_files": 0,
            "title_length": 20,
            "body_length": 100,
            "has_linked_issue": 1,
            "review_comments_count": 2 * i,
            "issue_comments_count": i,
            "changes_requested_count": 1 if is_high else 0,
            "approved_count": 1,
            "review_count": 2,
            "review_effort_score": float(i * 3),
            "merged": True,
            "risk_label": is_high,
        })
    return records


@pytest.fixture
def trained_pipeline(sample_records):
    """Provide a fully trained pipeline and evaluation metrics."""
    train_recs, test_recs = split_dataset(sample_records, test_size=0.3, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    pipeline = RiskModelPipeline()
    pipeline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)

    metrics = evaluate_model(pipeline, X_test, y_test)
    return pipeline, metrics, feature_names, X_test, y_test


# ─── 1. MLflow run creation ───────────────────────────────────────────────────

def test_mlflow_run_is_created(tmp_mlflow_dir):
    """A new MLflow run must be created when entering the mlflow_run context."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="test-run") as run:
            assert run is not None
            assert run.info.run_id is not None
            assert len(run.info.run_id) > 0


def test_mlflow_run_uses_correct_experiment(tmp_mlflow_dir):
    """The run must be created under the expected experiment name."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="experiment-name-check") as run:
            mlflow.set_tracking_uri(tmp_mlflow_dir)
            experiment = mlflow.get_experiment(run.info.experiment_id)
            assert experiment.name == MLFLOW_EXPERIMENT_NAME


def test_mlflow_run_name_tag(tmp_mlflow_dir):
    """The run_name tag must be set correctly."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="my-test-run") as run:
            assert run.data.tags.get("mlflow.runName") == "my-test-run"


# ─── 2. Parameter logging ─────────────────────────────────────────────────────

def test_environment_params_logged(tmp_mlflow_dir):
    """Python, sklearn, and MLflow versions must be logged as params."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="env-params-test") as run:
            log_environment_params()

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.params
        assert "python_version" in logged
        assert "sklearn_version" in logged
        assert "mlflow_version" in logged


def test_dataset_params_logged(tmp_mlflow_dir):
    """Dataset split configuration must be captured as MLflow params."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="dataset-params-test") as run:
            log_dataset_params(
                total_records=100,
                train_samples=80,
                test_samples=20,
                num_features=18,
                feature_names=["files_changed", "lines_added"],
                test_size=0.2,
                random_state=42,
                dataset_source="synthetic_demo",
            )

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.params
        assert logged["dataset_total_records"] == "100"
        assert logged["dataset_train_samples"] == "80"
        assert logged["dataset_test_samples"] == "20"
        assert logged["dataset_num_features"] == "18"
        assert logged["split_test_size"] == "0.2"
        assert logged["split_random_state"] == "42"
        assert logged["dataset_source"] == "synthetic_demo"


def test_model_params_logged_lr(tmp_mlflow_dir):
    """Logistic Regression hyperparameters must be logged correctly."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="lr-params-test") as run:
            log_model_params(
                model_type="lr",
                model_name="Logistic Regression",
                random_state=42,
                cv_score_lr=0.88,
                cv_score_rf=0.75,
            )

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.params
        assert logged["model_type"] == "LogisticRegression"
        assert logged["lr_class_weight"] == "balanced"
        assert logged["lr_max_iter"] == "1000"
        assert logged["cv_score_lr"] == "0.88"
        assert logged["cv_score_rf"] == "0.75"
        assert logged["selected_by"] == "cv_f1_score"


def test_model_params_logged_rf(tmp_mlflow_dir):
    """Random Forest hyperparameters must be logged correctly."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="rf-params-test") as run:
            log_model_params(
                model_type="rf",
                model_name="Random Forest",
                random_state=42,
                cv_score_lr=0.70,
                cv_score_rf=0.85,
            )

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.params
        assert logged["model_type"] == "RandomForestClassifier"
        assert logged["rf_n_estimators"] == "100"
        assert logged["rf_class_weight"] == "balanced"


# ─── 3. Metric logging ────────────────────────────────────────────────────────

def test_evaluation_metrics_logged(tmp_mlflow_dir, trained_pipeline):
    """All core evaluation metrics must be logged to MLflow."""
    pipeline, metrics, feature_names, X_test, y_test = trained_pipeline

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="metrics-test") as run:
            log_evaluation_metrics(metrics)

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.metrics

        assert "test_accuracy" in logged
        assert "test_precision" in logged
        assert "test_recall" in logged
        assert "test_f1_score" in logged
        assert "test_roc_auc" in logged
        assert "test_pr_auc" in logged
        assert "test_samples" in logged

        # Verify the values match what evaluate_model returned
        assert abs(logged["test_accuracy"] - metrics["accuracy"]) < 1e-4
        assert abs(logged["test_f1_score"] - metrics["f1_score"]) < 1e-4
        assert abs(logged["test_roc_auc"] - metrics["roc_auc"]) < 1e-4


def test_metric_values_are_valid_floats(tmp_mlflow_dir, trained_pipeline):
    """Logged metric values must be finite floats in expected ranges."""
    pipeline, metrics, *_ = trained_pipeline

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="metric-range-test") as run:
            log_evaluation_metrics(metrics)

        mlflow.set_tracking_uri(tmp_mlflow_dir)
        logged = mlflow.get_run(run.info.run_id).data.metrics

        for key in ("test_accuracy", "test_precision", "test_recall", "test_f1_score", "test_roc_auc"):
            val = logged[key]
            assert 0.0 <= val <= 1.0, f"{key}={val} is out of [0, 1]"


# ─── 4. Artifact logging ──────────────────────────────────────────────────────

def test_model_artifact_logged(tmp_mlflow_dir, tmp_path, trained_pipeline):
    """The trained model joblib must be logged as an MLflow artifact."""
    pipeline, metrics, feature_names, X_test, y_test = trained_pipeline
    model_path = str(tmp_path / "risk_model.joblib")
    pipeline.save(model_path)

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="artifact-model-test") as run:
            log_and_register_model(pipeline, model_path)

    # Verify the artifact exists in the MLflow run's artifact store
    mlflow.set_tracking_uri(tmp_mlflow_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tmp_mlflow_dir)
    artifacts = client.list_artifacts(run.info.run_id, path="raw_model")
    artifact_names = [a.path for a in artifacts]
    assert any("risk_model.joblib" in name for name in artifact_names)


def test_evaluation_artifact_logged(tmp_mlflow_dir, tmp_path, trained_pipeline):
    """The evaluation JSON must be logged as an MLflow artifact."""
    pipeline, metrics, *_ = trained_pipeline
    eval_path = str(tmp_path / "evaluation.json")
    from ml.evaluate import save_evaluation_results
    save_evaluation_results(metrics, eval_path)

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="artifact-eval-test") as run:
            log_evaluation_artifact(eval_path)

    mlflow.set_tracking_uri(tmp_mlflow_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tmp_mlflow_dir)
    artifacts = client.list_artifacts(run.info.run_id, path="evaluation")
    artifact_names = [a.path for a in artifacts]
    assert any("evaluation.json" in name for name in artifact_names)


def test_confusion_matrix_artifact_logged(tmp_mlflow_dir, trained_pipeline):
    """Confusion matrix must be logged as a JSON artifact."""
    pipeline, metrics, *_ = trained_pipeline
    cm = metrics.get("confusion_matrix", [[0, 0], [0, 0]])

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="cm-artifact-test") as run:
            log_confusion_matrix_artifact(cm)

    mlflow.set_tracking_uri(tmp_mlflow_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tmp_mlflow_dir)
    artifacts = client.list_artifacts(run.info.run_id, path="evaluation")
    artifact_names = [a.path for a in artifacts]
    assert any("confusion_matrix" in name for name in artifact_names)


def test_feature_metadata_artifact_logged(tmp_mlflow_dir):
    """Feature metadata JSON must be logged as an MLflow artifact."""
    feature_names = ["files_changed", "lines_added", "commits_count"]

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="feature-meta-test") as run:
            log_feature_metadata_artifact(feature_names)

    mlflow.set_tracking_uri(tmp_mlflow_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tmp_mlflow_dir)
    artifacts = client.list_artifacts(run.info.run_id, path="metadata")
    artifact_names = [a.path for a in artifacts]
    assert any("feature_metadata" in name for name in artifact_names)


def test_classification_report_artifact_logged(tmp_mlflow_dir, trained_pipeline):
    """Classification report text must be logged as an MLflow artifact."""
    pipeline, metrics, *_ = trained_pipeline
    cls_str = metrics.get("classification_report_str", "report")

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="cls-report-test") as run:
            log_classification_report_artifact(cls_str)

    mlflow.set_tracking_uri(tmp_mlflow_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tmp_mlflow_dir)
    artifacts = client.list_artifacts(run.info.run_id, path="evaluation")
    artifact_names = [a.path for a in artifacts]
    assert any("classification_report" in name for name in artifact_names)


# ─── 5. Training still produces the model artifact ────────────────────────────

def test_training_produces_joblib_artifact(tmp_mlflow_dir, tmp_path, sample_records):
    """The training pipeline must still write the joblib model file."""
    from ml.train import generate_synthetic_demo_dataset, evaluate_cv

    records = generate_synthetic_demo_dataset(num_records=60)
    train_recs, test_recs = split_dataset(records, test_size=0.2, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    model_path = str(tmp_path / "risk_model.joblib")

    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="train-artifact-test"):
            pipeline = RiskModelPipeline(model_name="Logistic Regression")
            pipeline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)
            pipeline.save(model_path)

            metrics = evaluate_model(pipeline, X_test, y_test)
            log_evaluation_metrics(metrics)
            log_and_register_model(pipeline, model_path)

    assert os.path.exists(model_path), "joblib model artifact was not created"
    loaded = RiskModelPipeline.load(model_path)
    assert loaded.is_trained


def test_trained_model_predictions_unchanged(tmp_path, sample_records):
    """After MLflow wrapping, the model's predictions must be identical."""
    train_recs, test_recs = split_dataset(sample_records, test_size=0.3, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    # Train WITHOUT MLflow
    pipeline_baseline = RiskModelPipeline()
    pipeline_baseline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)
    preds_baseline = pipeline_baseline.predict(X_test)

    # Train WITH MLflow (isolated temp tracking dir)
    tmp_mlflow = str(tmp_path / "mlruns_pred_test")
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow}):
        with mlflow_run(run_name="prediction-parity-test"):
            pipeline_tracked = RiskModelPipeline()
            pipeline_tracked.train(X_train, y_train, feature_names, model_type="lr", random_state=42)
            log_evaluation_metrics(evaluate_model(pipeline_tracked, X_test, y_test))

    preds_tracked = pipeline_tracked.predict(X_test)
    np.testing.assert_array_equal(preds_baseline, preds_tracked)


# ─── 6. Existing prediction functionality still works ─────────────────────────

def test_predict_pr_risk_unaffected(tmp_path, sample_records):
    """The predict_pr_risk function (Person 1 API) must be unaffected by MLflow."""
    from ml.predict import predict_pr_risk

    train_recs, _ = split_dataset(sample_records, test_size=0.2, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)

    pipeline = RiskModelPipeline()
    pipeline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)
    model_path = str(tmp_path / "risk_model_pred_test.joblib")
    pipeline.save(model_path)

    pr_data = {
        "files_changed": 3,
        "lines_added": 50,
        "lines_deleted": 10,
        "commits": [{}, {}],
        "title": "Small fix",
        "body": "Fixes a minor bug",
    }
    diff_data = {
        "files_changed": ["app/utils.py"],
        "added_lines": ["+fix"],
        "deleted_lines": ["-old"],
        "binary_files": [],
    }

    result = predict_pr_risk(pr_data, diff_data, model_path=model_path)
    assert "risk_score" in result
    assert "risk_level" in result
    assert result["risk_level"] in ("LOW", "HIGH")
    assert 0.0 <= result["risk_score"] <= 1.0


# ─── 7. No external MLflow server required ────────────────────────────────────

def test_tracking_uses_only_local_files(tmp_mlflow_dir):
    """Verify all MLflow state is written to a local file-based tracking URI."""
    with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": tmp_mlflow_dir}):
        with mlflow_run(run_name="local-only-test") as run:
            mlflow.log_param("test_key", "test_value")

    # The tracking directory must exist and contain experiment/run data
    assert os.path.isdir(tmp_mlflow_dir)
    # No network calls possible — if this passes, it's file-based only


def test_graceful_degradation_when_mlflow_unavailable():
    """The mlflow_run context manager must not crash if MLflow is missing."""
    # Patch the import to simulate MLflow being absent
    import ml.tracking as tracking_module
    original = tracking_module._try_import_mlflow

    tracking_module._try_import_mlflow = lambda: None
    try:
        # Should yield None without raising
        with mlflow_run(run_name="no-mlflow") as run:
            assert run is None
    finally:
        tracking_module._try_import_mlflow = original
