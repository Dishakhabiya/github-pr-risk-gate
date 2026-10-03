import os
from unittest.mock import patch
import numpy as np
import pytest

from ml.evaluate import evaluate_model, save_evaluation_results
from ml.model import RiskModelPipeline
from ml.preprocessing import (
    FORBIDDEN_OUTCOME_FIELDS,
    load_dataset,
    prepare_feature_matrix,
    split_dataset,
    validate_no_data_leakage,
)


@pytest.fixture
def sample_records():
    records = []
    for i in range(1, 30):
        is_high = 1 if i % 4 == 0 else 0
        records.append({
            "repository": "owner/repo",
            "pr_id": i,
            "created_at": f"2026-10-01T{i%24:02d}:00:00Z",
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
            # Outcome fields
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


def test_feature_target_separation(sample_records):
    X, y, feature_names = prepare_feature_matrix(sample_records)

    assert X.shape[0] == len(sample_records)
    assert len(y) == len(sample_records)
    assert len(feature_names) > 0


def test_review_outcome_columns_excluded(sample_records):
    _, _, feature_names = prepare_feature_matrix(sample_records)
    for forbidden in FORBIDDEN_OUTCOME_FIELDS:
        assert forbidden not in feature_names

    with pytest.raises(ValueError) as exc_info:
        validate_no_data_leakage(["files_changed", "review_comments_count"])
    assert "DATA LEAKAGE ERROR" in str(exc_info.value)


def test_risk_label_excluded(sample_records):
    _, _, feature_names = prepare_feature_matrix(sample_records)
    assert "risk_label" not in feature_names


def test_missing_value_handling():
    records_with_missing = [
        {
            "files_changed": None,
            "lines_added": "",
            "lines_deleted": 5,
            "risk_label": 0,
        }
    ]
    X, y, _ = prepare_feature_matrix(records_with_missing)
    pipeline = RiskModelPipeline(model_name="Test")
    X_scaled = pipeline.preprocessor.fit_transform(X)

    assert not np.isnan(X_scaled).any()


def test_model_training_and_predictions(sample_records):
    train_recs, test_recs = split_dataset(sample_records, test_size=0.3, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    pipeline = RiskModelPipeline()
    pipeline.train(X_train, y_train, feature_names, model_type="rf", random_state=42)

    preds = pipeline.predict(X_test)
    assert len(preds) == len(y_test)
    assert set(preds).issubset({0, 1})

    probs = pipeline.predict_proba(X_test)
    assert probs.shape == (len(y_test), 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))


def test_evaluation_metrics_produced(sample_records):
    train_recs, test_recs = split_dataset(sample_records, test_size=0.3, random_state=42)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    pipeline = RiskModelPipeline()
    pipeline.train(X_train, y_train, feature_names, model_type="lr", random_state=42)

    metrics = evaluate_model(pipeline, X_test, y_test)

    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "accuracy" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "confusion_matrix" in metrics


def test_saved_model_artifact_load(tmp_path, sample_records):
    X, y, feature_names = prepare_feature_matrix(sample_records)
    pipeline = RiskModelPipeline()
    pipeline.train(X, y, feature_names, model_type="rf", random_state=42)

    save_path = str(tmp_path / "model.joblib")
    pipeline.save(save_path)
    assert os.path.exists(save_path)

    loaded_pipeline = RiskModelPipeline.load(save_path)
    assert loaded_pipeline.is_trained
    assert loaded_pipeline.feature_names == feature_names

    preds_orig = pipeline.predict(X)
    preds_loaded = loaded_pipeline.predict(X)
    assert np.array_equal(preds_orig, preds_loaded)


def test_load_dataset(tmp_path):
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(
        "repository,pr_id,files_changed,risk_label\nowner/repo,1,5,0\nowner/repo,2,10,1\n"
    )

    records = load_dataset(str(csv_file))
    assert len(records) == 2
    assert records[0]["pr_id"] == 1
    assert records[0]["files_changed"] == 5
    assert records[1]["risk_label"] == 1
