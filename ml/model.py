import os
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml.preprocessing import DataPreprocessor


class RiskModelPipeline:
    """Wrapper pipeline bundling feature preprocessing, model estimation, and joblib serialization."""

    def __init__(self, model_name: str = "Random Forest"):
        self.model_name = model_name
        self.preprocessor = DataPreprocessor()
        self.model: Optional[Any] = None
        self.feature_names: List[str] = []
        self.is_trained = False

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: List[str],
        model_type: str = "rf",
        random_state: int = 42,
    ) -> None:
        """Fit preprocessing pipeline and model on training data.

        Args:
            X_train: Raw training feature matrix.
            y_train: Training target labels (0 or 1).
            feature_names: List of feature column names.
            model_type: 'rf' for Random Forest, 'lr' for Logistic Regression.
            random_state: Random seed for reproducibility.
        """
        self.feature_names = list(feature_names)

        # Fit preprocessing ONLY on training data
        X_train_scaled = self.preprocessor.fit_transform(X_train)

        if model_type.lower() in ("lr", "logistic", "logistic_regression"):
            self.model_name = "Logistic Regression"
            self.model = LogisticRegression(
                class_weight="balanced", random_state=random_state, max_iter=1000
            )
        else:
            self.model_name = "Random Forest"
            self.model = RandomForestClassifier(
                n_estimators=100, class_weight="balanced", random_state=random_state
            )

        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict binary risk labels (0 or 1) for input feature matrix.

        Args:
            X: Input feature matrix.

        Returns:
            1D numpy array of predicted labels (0 or 1).
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model pipeline is not trained yet.")
        X_scaled = self.preprocessor.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities for input feature matrix.

        Args:
            X: Input feature matrix.

        Returns:
            2D numpy array of shape (N, 2) where column 1 is the high-risk class probability.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model pipeline is not trained yet.")
        X_scaled = self.preprocessor.transform(X)
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X_scaled)
        else:
            # Fallback for models without predict_proba
            preds = self.model.predict(X_scaled)
            probs = np.zeros((len(preds), 2))
            probs[np.arange(len(preds)), preds] = 1.0
            return probs

    def save(self, filepath: str) -> None:
        """Save the pipeline object to disk using joblib.

        Args:
            filepath: Destination file path (e.g. artifacts/risk_model.joblib).
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "RiskModelPipeline":
        """Load a saved pipeline object from disk.

        Args:
            filepath: Path to saved .joblib artifact.

        Returns:
            Loaded RiskModelPipeline instance.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at: {filepath}")
        pipeline = joblib.load(filepath)
        if not isinstance(pipeline, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return pipeline
