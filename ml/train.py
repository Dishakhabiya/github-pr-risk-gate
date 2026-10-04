import argparse
import os
import sys
from typing import Any, Dict, List
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline as SklearnPipeline

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.dataset.labeler import FEATURE_COLUMNS, LABEL_COLUMN
from ml.evaluate import evaluate_model, print_evaluation_report, save_evaluation_results
from ml.model import RiskModelPipeline
from ml.preprocessing import (
    DataPreprocessor,
    load_dataset,
    prepare_feature_matrix,
    split_dataset,
)
from ml.tracking import (
    mlflow_run,
    log_environment_params,
    log_dataset_params,
    log_model_params,
    log_evaluation_metrics,
    log_and_register_model,
    log_evaluation_artifact,
    log_confusion_matrix_artifact,
    log_feature_metadata_artifact,
    log_classification_report_artifact,
)


def generate_synthetic_demo_dataset(num_records: int = 50) -> List[Dict[str, Any]]:
    """Generate synthetic records for demonstration/testing when CSV is not present."""
    records = []
    for i in range(1, num_records + 1):
        is_high = 1 if i > int(num_records * 0.8) else 0
        rec = {
            "repository": "demo/repo",
            "pr_id": i,
            "created_at": f"2026-10-01T{i%24:02d}:00:00Z",
            "files_changed": 2 if not is_high else 15,
            "lines_added": 20 if not is_high else 450,
            "lines_deleted": 5 if not is_high else 120,
            "total_lines_changed": 25 if not is_high else 570,
            "commits_count": 1 if not is_high else 8,
            "additions_to_deletions_ratio": 4.0 if not is_high else 3.75,
            "source_files_changed": 1 if not is_high else 10,
            "test_files_changed": 1 if not is_high else 3,
            "documentation_files_changed": 0,
            "config_files_changed": 0 if not is_high else 2,
            "average_changes_per_file": 12.5 if not is_high else 38.0,
            "binary_files_changed": 0,
            "renamed_files": 0,
            "deleted_files": 0,
            "added_files": 0 if not is_high else 3,
            "title_length": 30,
            "body_length": 200,
            "has_linked_issue": 1,
            # Outcome fields (Post-creation lifecycle data)
            "review_comments_count": 1 if not is_high else 12,
            "issue_comments_count": 2 if not is_high else 8,
            "changes_requested_count": 0 if not is_high else 2,
            "approved_count": 1,
            "review_count": 1 if not is_high else 4,
            "review_effort_score": 2.0 if not is_high else 18.0,
            "merged": True,
            "risk_label": is_high,
        }
        records.append(rec)
    return records


def evaluate_cv(
    model_type: str, X_train: np.ndarray, y_train: np.ndarray, random_state: int = 42
) -> float:
    """Evaluate candidate model architecture using 5-Fold Stratified CV strictly on training data."""
    preprocessor = DataPreprocessor()

    if model_type == "lr":
        clf = LogisticRegression(
            class_weight="balanced", random_state=random_state, max_iter=1000
        )
    else:
        clf = RandomForestClassifier(
            n_estimators=100, class_weight="balanced", random_state=random_state
        )

    cv_pipeline = SklearnPipeline([
        ("imputer", preprocessor.imputer),
        ("scaler", preprocessor.scaler),
        ("clf", clf),
    ])

    # Check if cross validation folds are possible (at least 2 classes)
    if len(np.unique(y_train)) < 2:
        return 0.0

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    scores = cross_val_score(cv_pipeline, X_train, y_train, cv=cv, scoring="f1", error_score=0.0)
    return float(np.mean(scores))


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate PR Risk Prediction Model.")
    parser.add_argument(
        "--csv-path",
        type=str,
        default="data/historical_prs.csv",
        help="Path to training dataset CSV file (default: data/historical_prs.csv).",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="artifacts/risk_model.joblib",
        help="Path to save trained model artifact (default: artifacts/risk_model.joblib).",
    )
    parser.add_argument(
        "--eval-path",
        type=str,
        default="artifacts/evaluation.json",
        help="Path to save evaluation metrics JSON (default: artifacts/evaluation.json).",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test set split fraction (default: 0.2).",
    )

    args = parser.parse_args()

    print("=== US-05/US-06 ML Training Pipeline ===")
    if os.path.exists(args.csv_path):
        print(f"Loading dataset from: {args.csv_path}")
        records = load_dataset(args.csv_path)
        dataset_source = args.csv_path
    else:
        print(f"Dataset CSV not found at {args.csv_path}. Generating synthetic demo dataset for training...")
        records = generate_synthetic_demo_dataset(num_records=100)
        dataset_source = "synthetic_demo"

    total_records = len(records)
    print(f"Total dataset records: {total_records}")

    # Split dataset into training set and untouched held-out test set
    train_recs, test_recs = split_dataset(
        records, test_size=args.test_size, random_state=args.random_state, use_chronological=False
    )

    # Extract feature matrices (strictly creation-time features)
    X_train, y_train, feature_names = prepare_feature_matrix(train_recs)
    X_test, y_test, _ = prepare_feature_matrix(test_recs)

    pos_labels = sum(1 for y in y_train if y == 1) + sum(1 for y in y_test if y == 1)
    neg_labels = total_records - pos_labels

    print(f"Number of features: {len(feature_names)}")
    print(f"Label distribution: {neg_labels} LOW RISK (0), {pos_labels} HIGH RISK (1)")
    print(f"Training samples: {len(train_recs)}")
    print(f"Held-out test samples: {len(test_recs)}\n")

    # Model Selection using Cross-Validation strictly on Training Data
    print("Performing 5-Fold Stratified Cross-Validation strictly on Training Data...")
    cv_score_lr = evaluate_cv("lr", X_train, y_train, random_state=args.random_state)
    cv_score_rf = evaluate_cv("rf", X_train, y_train, random_state=args.random_state)

    print(f"  - Logistic Regression Training CV F1-Score: {cv_score_lr:.4f}")
    print(f"  - Random Forest Training CV F1-Score:       {cv_score_rf:.4f}")

    if cv_score_rf >= cv_score_lr:
        selected_model_type = "rf"
        selected_model_name = "Random Forest"
    else:
        selected_model_type = "lr"
        selected_model_name = "Logistic Regression"

    print(f"\nSelected Model Architecture: {selected_model_name} (based on training CV F1-Score)")

    # ── US-18 MLflow Experiment Tracking ──────────────────────────────────────
    with mlflow_run(run_name=f"train-{selected_model_type}") as run:

        # 1. Environment params
        log_environment_params()

        # 2. Dataset & split params
        log_dataset_params(
            total_records=total_records,
            train_samples=len(train_recs),
            test_samples=len(test_recs),
            num_features=len(feature_names),
            feature_names=list(feature_names),
            test_size=args.test_size,
            random_state=args.random_state,
            dataset_source=dataset_source,
        )

        # 3. Model hyperparameters & selection params
        log_model_params(
            model_type=selected_model_type,
            model_name=selected_model_name,
            random_state=args.random_state,
            cv_score_lr=cv_score_lr,
            cv_score_rf=cv_score_rf,
        )

        # ── Train selected model pipeline on FULL Training Set ──────────────
        final_pipeline = RiskModelPipeline(model_name=selected_model_name)
        final_pipeline.train(
            X_train, y_train, feature_names, model_type=selected_model_type, random_state=args.random_state
        )

        # Save trained model pipeline artifact (joblib) — same path as before
        final_pipeline.save(args.model_path)
        print(f"Saved trained model artifact to: {args.model_path}")

        # ── Evaluate ONCE on untouched held-out test set ────────────────────
        test_metrics = evaluate_model(final_pipeline, X_test, y_test)

        # Save evaluation results JSON artifact
        save_evaluation_results(test_metrics, args.eval_path)
        print(f"Saved evaluation metrics to: {args.eval_path}")

        # 4. Log evaluation metrics to MLflow
        log_evaluation_metrics(test_metrics)

        # 5. Log and register artifacts to MLflow Model Registry
        log_and_register_model(final_pipeline, args.model_path)
        log_evaluation_artifact(args.eval_path)
        log_confusion_matrix_artifact(test_metrics.get("confusion_matrix", []))
        log_feature_metadata_artifact(list(feature_names))
        log_classification_report_artifact(
            test_metrics.get("classification_report_str", "")
        )

        if run is not None:
            print(f"\n[MLflow] Run ID: {run.info.run_id}")
            print(f"[MLflow] Experiment: {run.info.experiment_id}")
            print(f"[MLflow] Tracking URI: {run.info.artifact_uri}")

    # Print final concise evaluation report for held-out test set
    print_evaluation_report(
        test_metrics, artifact_path=args.model_path, eval_path=args.eval_path
    )


if __name__ == "__main__":
    main()
