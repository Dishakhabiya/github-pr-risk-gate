import json
import os
from typing import Any, Dict, Optional
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_model(pipeline: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
    """Evaluate a trained model pipeline strictly on held-out test data.

    Args:
        pipeline: Trained RiskModelPipeline instance.
        X_test: Unseen test feature matrix.
        y_test: Unseen test target array.

    Returns:
        Dict containing precision, recall, f1, accuracy, confusion matrix, roc_auc, pr_auc.
    """
    y_pred = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)

    # Probabilities for positive class (1 = HIGH RISK)
    if probs.ndim == 2 and probs.shape[1] > 1:
        y_prob = probs[:, 1]
    else:
        y_prob = probs

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()

    # ROC-AUC calculation
    try:
        if len(np.unique(y_test)) > 1:
            roc_auc = float(roc_auc_score(y_test, y_prob))
        else:
            roc_auc = 0.5
    except Exception:
        roc_auc = 0.5

    # PR-AUC / Average Precision calculation
    try:
        if len(np.unique(y_test)) > 1:
            pr_auc = float(average_precision_score(y_test, y_prob))
        else:
            pr_auc = 0.0
    except Exception:
        pr_auc = 0.0

    cls_report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
    cls_report_str = classification_report(y_test, y_pred, zero_division=0)

    return {
        "model_name": getattr(pipeline, "model_name", "RiskModel"),
        "test_samples": len(y_test),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": cm,
        "classification_report_dict": cls_report,
        "classification_report_str": cls_report_str,
    }


def print_evaluation_report(
    metrics: Dict[str, Any],
    artifact_path: Optional[str] = None,
    eval_path: Optional[str] = None,
) -> None:
    """Print formatted concise final evaluation summary report to stdout."""
    model_name = metrics.get("model_name", "Risk Model")
    samples = metrics.get("test_samples", 0)

    print(f"\n================ CONCISE FINAL EVALUATION SUMMARY ================")
    print(f"Selected Model:     {model_name}")
    print(f"Test Sample Count:  {samples}")
    print(f"------------------------------------------------------------------")
    print(f"Accuracy:           {metrics.get('accuracy', 0.0):.4f}")
    print(f"Precision:          {metrics.get('precision', 0.0):.4f}")
    print(f"Recall:             {metrics.get('recall', 0.0):.4f}")
    print(f"F1-Score:           {metrics.get('f1_score', 0.0):.4f}")
    print(f"ROC-AUC:            {metrics.get('roc_auc', 0.0):.4f}")
    print(f"PR-AUC:             {metrics.get('pr_auc', 0.0):.4f}")
    print(f"------------------------------------------------------------------")
    print("Confusion Matrix:")
    cm = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
    print(f"  [TN: {cm[0][0]:<4} FP: {cm[0][1]:<4}]")
    print(f"  [FN: {cm[1][0]:<4} TP: {cm[1][1]:<4}]")
    if artifact_path or eval_path:
        print(f"------------------------------------------------------------------")
        if artifact_path:
            print(f"Model Artifact:     {artifact_path}")
        if eval_path:
            print(f"Evaluation JSON:    {eval_path}")
    print("================================================------------------\n")


def save_evaluation_results(metrics: Dict[str, Any], filepath: str) -> None:
    """Save evaluation metrics dictionary to JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    clean_metrics = dict(metrics)
    clean_metrics.pop("classification_report_str", None)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean_metrics, f, indent=4)
