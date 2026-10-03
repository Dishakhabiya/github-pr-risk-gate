# US-07: Risk Prediction Module Documentation

## Overview
The `ml.predict` module provides a reusable, modular interface for evaluating Pull Request risk using a pre-trained ML model artifact saved at `artifacts/risk_model.joblib`.

This module is designed to be easily imported and invoked by FastAPI endpoints (Person 3) or background task workers.

---

## Key Design Principles

1. **No Retraining at Prediction Time**: Predicts probabilities using the pre-fitted model artifact loaded from `artifacts/risk_model.joblib`.
2. **Reuse Feature Engineering**: Reuses `US-03` feature extraction (`extract_features`) and `US-05` feature matrix scaling.
3. **Data Leakage Prevention**: Only creation-time features (`files_changed`, `lines_added`, `lines_deleted`, file type counts, etc.) are passed to the model. Post-creation outcome fields (`review_comments_count`, `changes_requested_count`, `merged`) are strictly rejected.
4. **Configurable Threshold**: Risk classification (`HIGH` vs `LOW`) uses a configurable cutoff parameter (default: `0.5`).

---

## Python Usage Examples

### Option 1: Prediction from raw US-01 PR data and US-02 diff data

```python
from ml.predict import predict_pr_risk

# Raw PR metadata from US-01 and diff from US-02
pr_data = {
    "pr_id": 1347,
    "title": "Fix critical buffer overflow in parser",
    "body": "Fixes #456",
    "changed_files": [{"filename": "src/parser.c", "status": "modified"}]
}
diff_data = {
    "files_changed": ["src/parser.c"],
    "num_added_lines": 120,
    "num_deleted_lines": 35,
    "binary_files": []
}

# Predict risk
result = predict_pr_risk(pr_data, diff_data, threshold=0.5)
print(result)
# Output:
# {
#     "pr_id": 1347,
#     "risk_score": 0.7842,
#     "risk_level": "HIGH",
#     "threshold": 0.5,
#     "model_name": "Logistic Regression"
# }
```

### Option 2: Prediction from pre-extracted feature dictionary

```python
from ml.predict import PRRiskPredictor

predictor = PRRiskPredictor(model_path="artifacts/risk_model.joblib")

features = {
    "files_changed": 5,
    "lines_added": 200,
    "lines_deleted": 50,
    "total_lines_changed": 250,
    "commits_count": 3,
    "additions_to_deletions_ratio": 4.0,
    "source_files_changed": 4,
    "test_files_changed": 1,
    "documentation_files_changed": 0,
    "config_files_changed": 0,
    "average_changes_per_file": 50.0,
    "binary_files_changed": 0,
    "renamed_files": 0,
    "deleted_files": 0,
    "added_files": 0,
    "title_length": 45,
    "body_length": 300,
    "has_linked_issue": 1
}

prediction = predictor.predict_from_features(features, threshold=0.5, pr_id=2048)
print(prediction)
```

---

## Error Handling

- **`FileNotFoundError`**: Raised if `artifacts/risk_model.joblib` is missing.
- **`ValueError`**: Raised if forbidden post-creation outcome fields are present in input features.
- **`RuntimeError`**: Raised if model loading or scaling fails.
