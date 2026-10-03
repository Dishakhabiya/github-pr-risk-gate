import csv
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.dataset.labeler import FEATURE_COLUMNS, LABEL_COLUMN, OUTCOME_COLUMNS

FORBIDDEN_OUTCOME_FIELDS = set(OUTCOME_COLUMNS) | {
    "risk_label",
    "closed_at",
    "merged_at",
    "turnaround_hours",
}


def load_dataset(csv_path: str) -> List[Dict[str, Any]]:
    """Load dataset records from a CSV file.

    Args:
        csv_path: Path to dataset CSV file.

    Returns:
        List of record dictionaries.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset file not found at path: {csv_path}")

    records: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_row: Dict[str, Any] = {}
            for k, v in row.items():
                if v == "" or v is None:
                    parsed_row[k] = None
                elif v == "True":
                    parsed_row[k] = True
                elif v == "False":
                    parsed_row[k] = False
                else:
                    # Attempt numeric conversion
                    try:
                        parsed_row[k] = int(v)
                    except ValueError:
                        try:
                            parsed_row[k] = float(v)
                        except ValueError:
                            parsed_row[k] = v
            records.append(parsed_row)
    return records


def validate_no_data_leakage(selected_features: List[str]) -> None:
    """Assert that no post-creation outcome fields are in selected features."""
    leaked = set(selected_features).intersection(FORBIDDEN_OUTCOME_FIELDS)
    if leaked:
        raise ValueError(
            f"DATA LEAKAGE ERROR! The following outcome fields were found in model features: {leaked}"
        )


def prepare_feature_matrix(
    records: List[Dict[str, Any]], feature_columns: Optional[List[str]] = None
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Extract feature matrix X and target vector y from dataset records.

    Args:
        records: List of dataset dict records.
        feature_columns: Optional explicit feature list. Defaults to FEATURE_COLUMNS.

    Returns:
        Tuple of (X_matrix, y_vector, feature_names_list).
    """
    selected_features = feature_columns if feature_columns is not None else FEATURE_COLUMNS
    validate_no_data_leakage(selected_features)

    X_list: List[List[float]] = []
    y_list: List[int] = []

    for r in records:
        row_vals = []
        for col in selected_features:
            val = r.get(col, 0.0)
            if val is None or val == "":
                val = 0.0
            row_vals.append(float(val))
        X_list.append(row_vals)

        target_val = r.get(LABEL_COLUMN, 0)
        y_list.append(int(target_val) if target_val is not None else 0)

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int64)
    return X, y, selected_features


def split_dataset(
    records: List[Dict[str, Any]],
    test_size: float = 0.2,
    random_state: int = 42,
    use_chronological: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split dataset into training and held-out test sets.

    Attempts a chronological split using 'created_at' if available and valid,
    otherwise falls back to stratified splitting with a fixed random seed.

    Args:
        records: List of dataset dict records.
        test_size: Proportion of test set (default: 0.2).
        random_state: Random seed for reproducibility.
        use_chronological: If True, attempts chronological ordering by created_at.

    Returns:
        Tuple of (train_records, test_records).
    """
    if not records:
        return [], []

    # Check if chronological sorting by created_at is viable
    has_timestamps = all(r.get("created_at") for r in records)
    if use_chronological and has_timestamps:
        sorted_records = sorted(records, key=lambda r: str(r.get("created_at", "")))
        split_idx = int(len(sorted_records) * (1.0 - test_size))
        train_records = sorted_records[:split_idx]
        test_records = sorted_records[split_idx:]
        return train_records, test_records

    # Stratified fallback split
    y_labels = [r.get(LABEL_COLUMN, 0) for r in records]
    # Check if stratification is possible (at least 2 classes with >= 2 instances)
    unique_classes, counts = np.unique(y_labels, return_counts=True)
    can_stratify = len(unique_classes) > 1 and all(c >= 2 for c in counts)

    train_recs, test_recs = train_test_split(
        records,
        test_size=test_size,
        random_state=random_state,
        stratify=y_labels if can_stratify else None,
    )
    return train_recs, test_recs


class DataPreprocessor:
    """Preprocesses feature matrices safely using median imputation and scaling."""

    def __init__(self):
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit imputer and scaler on training data and transform."""
        X_imp = self.imputer.fit_transform(X)
        X_scaled = self.scaler.fit_transform(X_imp)
        self.is_fitted = True
        return X_scaled

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform test or new data using fitted imputer and scaler."""
        if not self.is_fitted:
            raise RuntimeError("DataPreprocessor must be fitted before calling transform.")
        X_imp = self.imputer.transform(X)
        return self.scaler.transform(X_imp)
