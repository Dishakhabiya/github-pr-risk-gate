# MLflow Experiment Tracking (US-18)

This project integrates [MLflow](https://mlflow.org/) to track machine learning experiments during the PR Risk model training process.

## How it is configured

MLflow is configured to use a **local file-based tracking store** (`./mlruns`). No external MLflow server or cloud credentials are required. The integration gracefully degrades if MLflow is uninstalled—meaning `python -m ml.train` will simply skip logging if the `mlflow` package is not found.

Model registry and versioning features are intentionally **not implemented** in this phase (reserved for US-19).

## Running Model Training

You can run the existing training script exactly as before:

```bash
# Ensure your virtual environment is active
source .venv/bin/activate

# Run the training script
python -m ml.train
```

Behind the scenes, this will automatically create an MLflow run in the `pr-risk-prediction` experiment, log all parameters, metrics, and artifacts, and then complete. The standard prediction endpoints and artifacts (`artifacts/risk_model.joblib`) remain fully functional.

## Starting the MLflow UI

To view your experiment runs, open a terminal in the root of the repository and start the local MLflow tracking UI:

```bash
source .venv/bin/activate
mlflow ui
```

Then, open your browser to [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Tracked Information

Every time you run training, the following data is logged to MLflow:

### Parameters
* **Environment**: `python_version`, `sklearn_version`, `mlflow_version`, `platform`
* **Dataset**: `dataset_total_records`, `dataset_train_samples`, `dataset_test_samples`, `dataset_num_features`, `split_test_size`, `dataset_source`, `split_random_state`
* **Model Selection**: `model_type`, `model_name`, cross-validation scores (`cv_score_lr`, `cv_score_rf`), hyper-parameters (e.g. `rf_n_estimators`, `lr_max_iter`), and the selected architecture.

### Metrics
* `test_accuracy`, `test_precision`, `test_recall`, `test_f1_score`, `test_roc_auc`, `test_pr_auc`
* Individual precision/recall/f1-scores for both the `low_risk` and `high_risk` classes.

### Artifacts
* **`model/risk_model.joblib`**: The serialized sklearn pipeline.
* **`evaluation/evaluation.json`**: The core metrics dictionary.
* **`evaluation/confusion_matrix_*.json`**: A JSON representation of the confusion matrix.
* **`evaluation/classification_report_*.txt`**: The full text-based classification report.
* **`metadata/feature_metadata_*.json`**: Names and versions of the features used in training to guarantee reproducibility without data leakage.
