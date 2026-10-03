import os
from typing import Any, Dict, Optional

from app.dataset.labeler import check_has_linked_issue
from app.features.extractor import extract_features
from ml.model import RiskModelPipeline
from ml.preprocessing import prepare_feature_matrix, validate_no_data_leakage


class PRRiskPredictor:
    """Predictor service for evaluating Pull Request risk using trained model artifact."""

    def __init__(
        self,
        model_path: str = "artifacts/risk_model.joblib",
        default_threshold: float = 0.5,
    ):
        self.model_path = model_path
        self.default_threshold = default_threshold
        self._pipeline: Optional[RiskModelPipeline] = None

    def load_model(self) -> RiskModelPipeline:
        """Load and cache the trained RiskModelPipeline artifact.

        Raises:
            FileNotFoundError: If the model artifact does not exist at model_path.
            RuntimeError: If loading the artifact fails or is invalid.
        """
        if self._pipeline is not None:
            return self._pipeline

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Trained risk model artifact not found at '{self.model_path}'. "
                "Please run 'python -m ml.train' to train and generate the model artifact."
            )

        try:
            self._pipeline = RiskModelPipeline.load(self.model_path)
            return self._pipeline
        except Exception as e:
            raise RuntimeError(
                f"Failed to load risk prediction model artifact from '{self.model_path}': {e}"
            )

    def predict_from_features(
        self,
        feature_record: Dict[str, Any],
        threshold: Optional[float] = None,
        pr_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Predict risk score and level from a dictionary of creation-time features.

        Args:
            feature_record: Dict containing creation-time PR features.
            threshold: Optional risk threshold override (default: default_threshold).
            pr_id: Optional PR number override.

        Returns:
            Dict containing pr_id, risk_score, risk_level, threshold, model_name.
        """
        pipeline = self.load_model()
        cutoff = threshold if threshold is not None else self.default_threshold

        pr_number = pr_id if pr_id is not None else feature_record.get("pr_id", 0)

        # Validate no outcome fields in feature record
        validate_no_data_leakage(list(feature_record.keys()))

        # Prepare feature matrix matching trained pipeline's feature names
        X, _, _ = prepare_feature_matrix(
            [feature_record], feature_columns=pipeline.feature_names
        )

        # Predict high-risk class probability using saved model without retraining
        probs = pipeline.predict_proba(X)
        if probs.ndim == 2 and probs.shape[1] > 1:
            high_risk_prob = float(probs[0, 1])
        else:
            high_risk_prob = float(probs[0])

        risk_score = round(high_risk_prob, 4)
        risk_level = "HIGH" if risk_score >= cutoff else "LOW"

        return {
            "pr_id": pr_number,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "threshold": cutoff,
            "model_name": getattr(pipeline, "model_name", "RiskModel"),
        }

    def predict_pr_risk(
        self,
        pr_data: Dict[str, Any],
        diff_data: Dict[str, Any],
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Predict risk score and level from raw US-01 pr_data and US-02 diff_data.

        Args:
            pr_data: Raw PR data dict from US-01.
            diff_data: Preprocessed diff dict from US-02.
            threshold: Optional risk threshold override.

        Returns:
            Dict containing pr_id, risk_score, risk_level, threshold, model_name.
        """
        # Extract features using US-03
        features = extract_features(pr_data, diff_data)

        # Creation-time text features
        title = pr_data.get("title") or ""
        body = pr_data.get("body") or ""
        features["title_length"] = len(title)
        features["body_length"] = len(body)
        features["has_linked_issue"] = check_has_linked_issue(title, body)

        pr_number = pr_data.get("pr_id") or pr_data.get("number", 0)
        return self.predict_from_features(features, threshold=threshold, pr_id=pr_number)


def predict_pr_risk(
    pr_data: Dict[str, Any],
    diff_data: Dict[str, Any],
    model_path: str = "artifacts/risk_model.joblib",
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Convenience helper function to predict PR risk score and level."""
    predictor = PRRiskPredictor(model_path=model_path, default_threshold=threshold)
    return predictor.predict_pr_risk(pr_data, diff_data, threshold=threshold)
