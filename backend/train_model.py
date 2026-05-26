from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

FEATURE_COLUMNS = [
    "Gender",
    "Married",
    "Dependents",
    "Education",
    "Self_Employed",
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History",
    "Property_Area",
]
TARGET_COLUMN = "Loan_Status"

NUMERIC_COLUMNS = [
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History",
]

CATEGORICAL_COLUMNS = [
    "Gender",
    "Married",
    "Dependents",
    "Education",
    "Self_Employed",
    "Property_Area",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoanEase credit underwriting model.")
    parser.add_argument(
        "--data",
        default="data/loan_train.csv",
        help="Path to Kaggle loan_train.csv dataset.",
    )
    parser.add_argument(
        "--artifacts",
        default="artifacts",
        help="Directory to save trained artifacts.",
    )
    return parser.parse_args()


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Download Kaggle loan_train.csv and place it there."
        )

    df = pd.read_csv(path)
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return df


def build_preprocessor(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict]:
    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    medians = {col: float(X[col].median()) for col in NUMERIC_COLUMNS}
    modes = {col: str(X[col].mode(dropna=True)[0]) for col in CATEGORICAL_COLUMNS}

    for col in NUMERIC_COLUMNS:
        X[col] = X[col].fillna(medians[col])
    for col in CATEGORICAL_COLUMNS:
        X[col] = X[col].fillna(modes[col]).astype(str)

    feature_encoders: dict[str, LabelEncoder] = {}
    for col in CATEGORICAL_COLUMNS:
        enc = LabelEncoder()
        X[col] = enc.fit_transform(X[col])
        feature_encoders[col] = enc

    target_encoder = LabelEncoder()
    y_encoded = target_encoder.fit_transform(y.astype(str))

    preprocessor = {
        "feature_columns": FEATURE_COLUMNS,
        "numeric_columns": NUMERIC_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "medians": medians,
        "modes": modes,
        "feature_encoders": feature_encoders,
        "target_encoder": target_encoder,
    }

    return X, y_encoded, preprocessor


def train_model(X: pd.DataFrame, y: pd.Series) -> tuple[XGBClassifier, dict]:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    base_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
    )

    param_grid = {
        "max_depth": [3, 4, 5],
        "n_estimators": [100, 200],
        "learning_rate": [0.05, 0.1, 0.2],
    }

    grid = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=5,
        scoring="accuracy",
        n_jobs=1,
        verbose=1,
    )
    grid.fit(X_train, y_train)

    best_model: XGBClassifier = grid.best_estimator_
    y_pred = best_model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    report_dict = classification_report(y_test, y_pred, output_dict=True)
    report_text = classification_report(y_test, y_pred)
    matrix = confusion_matrix(y_test, y_pred)

    print("\nBest Params:", grid.best_params_)
    print("\nClassification Report:\n", report_text)
    print("Confusion Matrix:\n", matrix)

    metrics = {
        "accuracy": float(accuracy),
        "classification_report": report_dict,
        "confusion_matrix": matrix.tolist(),
        "best_params": grid.best_params_,
    }
    return best_model, metrics


def save_artifacts(model: XGBClassifier, preprocessor: dict, metrics: dict, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    preprocessor["model_version"] = model_version
    preprocessor["metrics"] = metrics

    joblib.dump(model, artifacts_dir / "loan_model.pkl")
    joblib.dump(preprocessor, artifacts_dir / "preprocessor.pkl")

    metadata = {
        "model_version": model_version,
        "accuracy": metrics["accuracy"],
        "best_params": metrics["best_params"],
    }
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    artifacts_dir = Path(args.artifacts)

    dataset = load_dataset(data_path)
    X, y, preprocessor = build_preprocessor(dataset)
    model, metrics = train_model(X, y)
    save_artifacts(model, preprocessor, metrics, artifacts_dir)

    print(f"\nSaved model to: {artifacts_dir / 'loan_model.pkl'}")
    print(f"Saved preprocessor to: {artifacts_dir / 'preprocessor.pkl'}")


if __name__ == "__main__":
    main()
