"""
MLflow experiment tracking integration for the PR Risk Prediction training pipeline.

This module provides a single context-manager function `mlflow_run` that wraps
the existing training workflow and records all reproducible experiment information.

Design decisions:
- Zero changes to RiskModelPipeline, evaluate_model, or any prediction API.
- Uses a local file-based MLflow tracking store (./mlruns) by default.
- Falls back gracefully if MLflow is unavailable (import error) so the training
  pipeline still works without MLflow installed.
- Intentionally does NOT use the MLflow Model Registry (US-19).
"""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import numpy as np

MLFLOW_EXPERIMENT_NAME = "pr-risk-prediction"
MLFLOW_TRACKING_URI_ENV = "MLFLOW_TRACKING_URI"
DEFAULT_MLFLOW_TRACKING_DIR = "sqlite:///mlflow.db"


def _get_tracking_uri() -> str:
    """Return the MLflow tracking URI, respecting the environment variable override."""
    env_uri = os.environ.get(MLFLOW_TRACKING_URI_ENV)
    if env_uri:
        return env_uri
    return DEFAULT_MLFLOW_TRACKING_DIR


def _try_import_mlflow():
    """Try importing mlflow; return the module or None if unavailable."""
    try:
        import mlflow  # noqa: PLC0415
        return mlflow
    except ImportError:
        return None


@contextmanager
def mlflow_run(run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Context manager that starts a local MLflow run and yields the active run.

    Usage::

        with mlflow_run("training-run") as run:
            mlflow_log_params(...)
            mlflow_log_metrics(...)
            # train / evaluate ...

    If MLflow is not installed, yields None and logs a warning.
    """
    mlflow = _try_import_mlflow()
    if mlflow is None:
        print("[MLflow] WARNING: mlflow package not installed. Tracking skipped.")
        yield None
        return

    tracking_uri = _get_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    run_tags = {"mlflow.runName": run_name or "training"} if run_name else {}
    if tags:
        run_tags.update(tags)

    with mlflow.start_run(run_name=run_name, tags=run_tags) as run:
        yield run


# ─── Parameter logging helpers ───────────────────────────────────────────────

def log_environment_params() -> None:
    """Log Python, scikit-learn, and MLflow versions as run parameters."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    import sklearn  # noqa: PLC0415

    mlflow.log_params({
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "mlflow_version": mlflow.__version__,
        "platform": platform.system(),
    })


def log_dataset_params(
    total_records: int,
    train_samples: int,
    test_samples: int,
    num_features: int,
    feature_names: List[str],
    test_size: float,
    random_state: int,
    dataset_source: str,
) -> None:
    """Log dataset and split configuration as MLflow parameters."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    mlflow.log_params({
        "dataset_total_records": total_records,
        "dataset_train_samples": train_samples,
        "dataset_test_samples": test_samples,
        "dataset_num_features": num_features,
        "dataset_source": dataset_source,
        "split_test_size": test_size,
        "split_random_state": random_state,
        "split_strategy": "stratified_random",
        "feature_version": "v1",
    })

    # Log feature names as a JSON artifact tag (too long for a param)
    mlflow.set_tag("feature_names_json", json.dumps(feature_names))


def log_rag_params(**kwargs) -> None:
    """Log RAG specific parameters."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return
    mlflow.log_params(kwargs)


def log_model_params(
    model_type: str,
    model_name: str,
    random_state: int,
    cv_score_lr: float,
    cv_score_rf: float,
) -> None:
    """Log model type, architecture selection, and hyperparameters."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    # Model-specific hyperparameters
    if model_type == "lr":
        hyperparams = {
            "model_type": "LogisticRegression",
            "model_name": model_name,
            "lr_class_weight": "balanced",
            "lr_max_iter": 1000,
            "lr_random_state": random_state,
        }
    else:
        hyperparams = {
            "model_type": "RandomForestClassifier",
            "model_name": model_name,
            "rf_n_estimators": 100,
            "rf_class_weight": "balanced",
            "rf_random_state": random_state,
        }

    # Preprocessing configuration
    hyperparams.update({
        "preprocessing_imputer_strategy": "median",
        "preprocessing_scaler": "StandardScaler",
        "cv_folds": 5,
        "cv_scoring": "f1",
        "cv_score_lr": round(cv_score_lr, 4),
        "cv_score_rf": round(cv_score_rf, 4),
        "selected_by": "cv_f1_score",
    })

    mlflow.log_params(hyperparams)


# ─── Metric logging helpers ───────────────────────────────────────────────────

def log_evaluation_metrics(metrics: Dict[str, Any]) -> None:
    """Log all evaluation metrics from evaluate_model() output to MLflow."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    scalar_metrics = {
        "test_accuracy": metrics.get("accuracy", 0.0),
        "test_precision": metrics.get("precision", 0.0),
        "test_recall": metrics.get("recall", 0.0),
        "test_f1_score": metrics.get("f1_score", 0.0),
        "test_roc_auc": metrics.get("roc_auc", 0.0),
        "test_pr_auc": metrics.get("pr_auc", 0.0),
        "test_samples": float(metrics.get("test_samples", 0)),
    }
    mlflow.log_metrics(scalar_metrics)

    # Per-class metrics from classification report dict
    cls_report = metrics.get("classification_report_dict", {})
    for class_label, class_metrics in cls_report.items():
        if isinstance(class_metrics, dict):
            label_str = "low_risk" if class_label == "0" else "high_risk" if class_label == "1" else class_label
            for metric_name, value in class_metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"test_{label_str}_{metric_name}", float(value))


def log_llm_metrics(**kwargs) -> None:
    """Log LLM specific metrics."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return
    mlflow.log_metrics(kwargs)


# ─── Artifact logging helpers ─────────────────────────────────────────────────

REGISTERED_MODEL_NAME = "pr-risk-model"

def log_and_register_model(pipeline: Any, model_path: str) -> None:
    """Log the trained model using sklearn flavor and register it in the MLflow Model Registry."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return
        
    # Still log the raw joblib artifact for backwards compatibility
    if os.path.exists(model_path):
        mlflow.log_artifact(model_path, artifact_path="raw_model")
        
    # Log as MLflow model and register to Model Registry
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mlflow.sklearn.log_model(
                pipeline, 
                "model", 
                registered_model_name=REGISTERED_MODEL_NAME,
                skops_trusted_types=[
                    "ml.model.RiskModelPipeline",
                    "ml.preprocessing.DataPreprocessor",
                    "numpy.dtype",
                ],
            )
    except Exception as e:
        print(f"[MLflow] WARNING: Failed to log/register sklearn model: {e}")



def log_evaluation_artifact(eval_path: str) -> None:
    """Log the evaluation JSON artifact to MLflow."""
    mlflow = _try_import_mlflow()
    if mlflow is None or not os.path.exists(eval_path):
        return
    mlflow.log_artifact(eval_path, artifact_path="evaluation")


def log_confusion_matrix_artifact(confusion_matrix: List[List[int]]) -> None:
    """Write the confusion matrix to a temp JSON file and log it as an artifact."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    cm_data = {
        "confusion_matrix": confusion_matrix,
        "labels": ["LOW_RISK (0)", "HIGH_RISK (1)"],
        "layout": "[[TN, FP], [FN, TP]]",
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="confusion_matrix_", delete=False
    ) as f:
        json.dump(cm_data, f, indent=2)
        tmp_path = f.name

    try:
        mlflow.log_artifact(tmp_path, artifact_path="evaluation")
    finally:
        os.unlink(tmp_path)


def log_feature_metadata_artifact(
    feature_names: List[str],
    feature_version: str = "v1",
) -> None:
    """Write feature metadata to a temp JSON file and log it as an artifact."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    metadata = {
        "feature_version": feature_version,
        "num_features": len(feature_names),
        "feature_names": feature_names,
        "preprocessing": {
            "imputer": "SimpleImputer(strategy='median')",
            "scaler": "StandardScaler",
        },
        "note": "Only creation-time features are used. No post-creation outcome fields.",
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="feature_metadata_", delete=False
    ) as f:
        json.dump(metadata, f, indent=2)
        tmp_path = f.name

    try:
        mlflow.log_artifact(tmp_path, artifact_path="metadata")
    finally:
        os.unlink(tmp_path)


def log_classification_report_artifact(cls_report_str: str) -> None:
    """Log the full classification report text as an artifact."""
    mlflow = _try_import_mlflow()
    if mlflow is None:
        return

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="classification_report_", delete=False
    ) as f:
        f.write(cls_report_str)
        tmp_path = f.name

    try:
        mlflow.log_artifact(tmp_path, artifact_path="evaluation")
    finally:
        os.unlink(tmp_path)
