import os
import json
import logging
import openai
from typing import Any, Dict, List, Optional

from app.dataset.labeler import check_has_linked_issue
from app.features.extractor import extract_features
from ml.model import RiskModelPipeline
from ml.preprocessing import prepare_feature_matrix, validate_no_data_leakage

logger = logging.getLogger(__name__)

def get_llm_risk_score(pr_data: Dict[str, Any], diff_data: Dict[str, Any], context_chunks: List[Dict[str, Any]] = None) -> Optional[float]:
    """Uses an LLM to predict the risk score based on the semantic meaning of the code diff and RAG context."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
        
    client = openai.OpenAI(api_key=api_key)
    
    context_text = ""
    if context_chunks:
        context_text = "Repository Context (Guidelines and similar PRs):\n" + "\n".join([c.get("content", "") for c in context_chunks])
        context_text = context_text[:3000] # truncate context
        
    diff_text = json.dumps(diff_data)[:4000] # Truncate to avoid context limit issues
    prompt = f"""
    You are an expert security and code reviewer. Analyze the following Pull Request diff and determine the risk of bugs, regressions, or security vulnerabilities.
    Consider the provided repository context if available. Pay special attention to large deletions (which might just be safe dead-code removal).
    Return a risk score between 0.0 (completely safe) and 1.0 (extremely dangerous).
    
    PR Title: {pr_data.get('title')}
    
    {context_text}
    
    PR Diff: 
    {diff_text}
    
    Respond strictly with a JSON object matching this schema: {{"risk_score": <float>}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a senior technical PR reviewer."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        parsed = json.loads(response.choices[0].message.content)
        return float(parsed.get("risk_score", 0.5))
    except Exception as e:
        logger.error(f"LLM Risk Prediction failed: {e}")
        return None


DEFAULT_MODEL_PATH = "models:/pr-risk-model/latest"


class PRRiskPredictor:
    """Predictor service for evaluating Pull Request risk using trained model artifact."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        default_threshold: float = 0.5,
    ):
        # Default to MLflow registry version, fallback will occur in load_model
        self.model_path = model_path or DEFAULT_MODEL_PATH
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

        # Use MLflow registry if path starts with models:/
        if str(self.model_path).startswith("models:/"):
            try:
                import mlflow
                from ml.tracking import _get_tracking_uri
                mlflow.set_tracking_uri(_get_tracking_uri())
                self._pipeline = mlflow.sklearn.load_model(self.model_path)
                return self._pipeline
            except ImportError:
                print("[MLflow] Warning: MLflow not installed. Falling back to local joblib artifact.")
            except Exception as e:
                print(f"[MLflow] Warning: Failed to load MLflow model '{self.model_path}' ({e}). Falling back to local joblib artifact.")
                
            # If MLflow load fails, fallback to default artifact path only if model_path is default
            if self.model_path == DEFAULT_MODEL_PATH:
                self.model_path = "artifacts/risk_model.joblib"
            else:
                raise FileNotFoundError(
                    f"Trained risk model artifact not found at '{self.model_path}'. "
                    "Please run 'python -m ml.train' to train and generate the model artifact."
                )

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
        ml_result = self.predict_from_features(features, threshold=threshold, pr_id=pr_number)
        
        return ml_result

def predict_pr_risk(
    pr_data: Dict[str, Any],
    diff_data: Dict[str, Any],
    model_path: Optional[str] = None,
    threshold: float = 0.5,
    context_chunks: Optional[list] = None
) -> Dict[str, Any]:
    """Convenience helper function to predict PR risk score and level."""
    predictor = PRRiskPredictor(model_path=model_path, default_threshold=threshold)
    ml_result = predictor.predict_pr_risk(pr_data, diff_data, threshold=threshold)
    
    # IMPROVEMENT: Get semantic risk score from LLM using RAG Context
    llm_risk_score = get_llm_risk_score(pr_data, diff_data, context_chunks)
    
    if llm_risk_score is not None:
        # If LLM is extremely confident it's safe (e.g. dead code deletion), OVERRIDE the ML model entirely
        if llm_risk_score <= 0.2 and ml_result["risk_score"] > 0.5:
            final_score = llm_risk_score
            model_name = "LLM Override (Safe Deletion detected)"
        else:
            # Otherwise, blend 50% ML Model (Statistics) and 50% LLM (Semantic Logic)
            final_score = (ml_result["risk_score"] + llm_risk_score) / 2.0
            model_name = ml_result["model_name"] + " + LLM Semantic Analysis"
            
        ml_result["risk_score"] = round(final_score, 4)
        ml_result["risk_level"] = "HIGH" if final_score >= threshold else "LOW"
        ml_result["model_name"] = model_name
        
    return ml_result
