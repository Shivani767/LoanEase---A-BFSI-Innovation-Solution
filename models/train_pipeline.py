"""
LoanEase Credit Underwriting â€” Multi-Dataset Training Pipeline
==============================================================
Datasets  : Kaggle Loan Prediction Â· UCI Credit Approval
            German Credit (Statlog) Â· Home Credit Default Risk (sampled)
Models    : XGBoost Â· LightGBM Â· RandomForest Â· LogisticRegression
            Â· GradientBoosting  (5-fold CV comparison)
Tuning    : RandomizedSearchCV (50 iterations, roc_auc)
Outputs   : models/loan_model.pkl Â· models/preprocessor.pkl
            models/model_metadata.json
Run from project root:  python models/train_pipeline.py
"""

import json
import os
import sys
import time
import urllib.request
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

warnings.filterwarnings("ignore")

# â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT = Path(__file__).resolve().parent.parent          # project root
DATA_DIR = ROOT / "backend" / "data"
MODELS_DIR = ROOT / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# â”€â”€ EMI helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def calculate_emi(principal: float, annual_rate: float, months: int) -> float:
    if months <= 0:
        return 0.0
    if annual_rate == 0:
        return principal / months
    r = annual_rate / (12 * 100)
    try:
        emi = (principal * r * (1 + r) ** months) / ((1 + r) ** months - 1)
        return float(emi)
    except Exception:
        return 0.0


# â”€â”€ Step 1 â€” Download public datasets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def download_datasets() -> None:
    print("\n[1/6] Checking / downloading datasets...")

    uci_path = DATA_DIR / "uci_credit.csv"
    if not uci_path.exists():
        print("  â†’ Downloading UCI Credit Approval...")
        try:
            urllib.request.urlretrieve(
                "https://archive.ics.uci.edu/ml/machine-learning-databases"
                "/credit-screening/crx.data",
                str(uci_path),
            )
            print("  âœ“ UCI Credit downloaded")
        except Exception as exc:
            print(f"  âœ— UCI Credit download failed: {exc}")
    else:
        print("  âœ“ UCI Credit already present")

    german_path = DATA_DIR / "german_credit.csv"
    if not german_path.exists():
        print("  â†’ Downloading German Credit (Statlog)...")
        try:
            urllib.request.urlretrieve(
                "https://archive.ics.uci.edu/ml/machine-learning-databases"
                "/statlog/german/german.data",
                str(german_path),
            )
            print("  âœ“ German Credit downloaded")
        except Exception as exc:
            print(f"  âœ— German Credit download failed: {exc}")
    else:
        print("  âœ“ German Credit already present")

    home_path = DATA_DIR / "home_credit_sample.csv"
    if not home_path.exists():
        print("  â†’ Home Credit not found â€” generating synthetic sample (1 000 rows)...")
        rng = np.random.default_rng(42)
        n = 1000
        pd.DataFrame(
            {
                "AMT_INCOME_TOTAL": rng.normal(50_000, 20_000, n).clip(10_000),
                "AMT_CREDIT": rng.normal(500_000, 200_000, n).clip(50_000),
                "AMT_ANNUITY": rng.normal(20_000, 5_000, n).clip(3_000),
                "DAYS_BIRTH": rng.integers(-25_000, -7_000, n),
                "DAYS_EMPLOYED": rng.integers(-15_000, 0, n),
                "CNT_CHILDREN": rng.integers(0, 4, n),
                "NAME_EDUCATION_TYPE": rng.choice(
                    ["Higher education", "Secondary / secondary special"], n
                ),
                "NAME_INCOME_TYPE": rng.choice(
                    ["Working", "Commercial associate"], n
                ),
                "CODE_GENDER": rng.choice(["M", "F"], n),
                "TARGET": rng.choice([0, 1], n, p=[0.9, 0.1]),
            }
        ).to_csv(home_path, index=False)
        print("  âœ“ Synthetic Home Credit sample created")
    else:
        print("  âœ“ Home Credit sample already present")


# â”€â”€ Step 2 â€” Load & standardise each dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
STANDARD_COLS = [
    "income", "loan_amount", "loan_term_months", "credit_history",
    "employment_type", "education", "dependents", "gender",
    "coapplicant_income", "property_area", "target",
]

def _fill_nulls(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["income", "loan_amount", "loan_term_months",
                "coapplicant_income", "dependents"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    for col in ["employment_type", "education", "gender",
                "property_area", "credit_history"]:
        if col in df.columns:
            mode = df[col].mode()
            df[col] = df[col].fillna(mode[0] if not mode.empty else "unknown")
    return df


def load_and_standardize(dataset_name: str, filepath: str) -> pd.DataFrame:
    print(f"  Loading {dataset_name}â€¦", end=" ")
    if not os.path.exists(filepath):
        print(f"SKIPPED (file not found: {filepath})")
        return pd.DataFrame()

    std = pd.DataFrame()

    if dataset_name == "kaggle_loan":
        df = pd.read_csv(filepath)
        std["income"] = df["ApplicantIncome"]
        std["loan_amount"] = df["LoanAmount"] * 1000
        std["loan_term_months"] = df["Loan_Amount_Term"]
        std["credit_history"] = df["Credit_History"]
        std["employment_type"] = df["Self_Employed"].map(
            {"Yes": "self_employed", "No": "salaried"}
        )
        std["education"] = df["Education"].map(
            {"Graduate": "graduate", "Not Graduate": "not_graduate"}
        )
        std["dependents"] = (
            df["Dependents"].replace("3+", "3").astype(float)
        )
        std["gender"] = df["Gender"].str.lower()
        std["coapplicant_income"] = df["CoapplicantIncome"]
        std["property_area"] = df["Property_Area"].str.lower()
        std["target"] = df["Loan_Status"].map({"Y": 1, "N": 0})

    elif dataset_name == "uci_credit":
        df = pd.read_csv(filepath, header=None, na_values="?")
        std["income"] = pd.to_numeric(df[2], errors="coerce") * 1000
        std["loan_amount"] = pd.to_numeric(df[7], errors="coerce") * 1000
        std["loan_term_months"] = 360
        std["credit_history"] = 1
        std["employment_type"] = "salaried"
        std["education"] = "graduate"
        std["dependents"] = 0
        std["gender"] = "male"
        std["coapplicant_income"] = pd.to_numeric(df[14], errors="coerce").fillna(0)
        std["property_area"] = "urban"
        std["target"] = df[15].map({"+": 1, "-": 0})

    elif dataset_name == "german_credit":
        df = pd.read_csv(filepath, sep=" ", header=None)
        std["loan_amount"] = pd.to_numeric(df[4], errors="coerce")
        std["loan_term_months"] = pd.to_numeric(df[1], errors="coerce")
        std["income"] = std["loan_amount"] / 12
        std["credit_history"] = 1
        std["employment_type"] = "salaried"
        std["education"] = "graduate"
        age_col = pd.to_numeric(df[12], errors="coerce").fillna(30)
        std["dependents"] = (age_col > 30).astype(int)
        std["gender"] = "male"
        std["coapplicant_income"] = 0.0
        std["property_area"] = "urban"
        std["target"] = pd.to_numeric(df[20], errors="coerce").map({1: 1, 2: 0})

    elif dataset_name == "home_credit":
        df = pd.read_csv(filepath)
        annuity = pd.to_numeric(df["AMT_ANNUITY"], errors="coerce").clip(lower=1)
        credit = pd.to_numeric(df["AMT_CREDIT"], errors="coerce").clip(lower=1)
        std["income"] = pd.to_numeric(df["AMT_INCOME_TOTAL"], errors="coerce") / 12
        std["loan_amount"] = credit
        std["loan_term_months"] = (credit / annuity).fillna(36).clip(1, 360).astype(int)
        std["credit_history"] = 1
        std["employment_type"] = "salaried"
        std["education"] = df["NAME_EDUCATION_TYPE"].apply(
            lambda x: "graduate" if "Higher" in str(x) else "not_graduate"
        )
        std["dependents"] = pd.to_numeric(df["CNT_CHILDREN"], errors="coerce").fillna(0)
        std["gender"] = (
            df["CODE_GENDER"].str.lower().map({"m": "male", "f": "female"}).fillna("male")
        )
        std["coapplicant_income"] = 0.0
        std["property_area"] = "urban"
        # TARGET: 0=goodâ†’1 approved, 1=defaultâ†’0 rejected
        std["target"] = pd.to_numeric(df["TARGET"], errors="coerce").map({0: 1, 1: 0})

    else:
        print("SKIPPED (unknown dataset name)")
        return pd.DataFrame()

    std = _fill_nulls(std)
    rows_before = len(std)
    std = std.dropna(subset=["target"])
    print(f"{len(std)} rows  (dropped {rows_before - len(std)} nulls)")
    return std


# â”€â”€ Step 3 â€” Feature engineering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["debt_to_income"] = (
        df["loan_amount"]
        / (df["income"].clip(lower=1) * df["loan_term_months"].clip(lower=1))
    ).clip(0, 10)

    df["total_income"] = df["income"] + df["coapplicant_income"]

    df["income_per_dependent"] = df.apply(
        lambda r: r["total_income"] / max(r["dependents"] + 1, 1), axis=1
    )

    df["loan_to_income"] = df["loan_amount"] / df["total_income"].clip(lower=1)

    df["estimated_emi"] = df.apply(
        lambda r: calculate_emi(r["loan_amount"], 12.0, int(r["loan_term_months"])),
        axis=1,
    )

    df["emi_to_income"] = df["estimated_emi"] / df["total_income"].clip(lower=1)

    return df


# â”€â”€ Step 4 â€” Build preprocessor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    num_feats = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
    cat_feats = X.select_dtypes(include=["object", "category"]).columns.tolist()

    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer([
        ("num", num_pipe, num_feats),
        ("cat", cat_pipe, cat_feats),
    ]), num_feats, cat_feats


# â”€â”€ Step 5 â€” Model comparison â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def compare_models(X_train, y_train, X_test, y_test) -> tuple:
    models = {
        "XGBoost": XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", random_state=42,
        ),
        "LightGBM": LGBMClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            random_state=42, verbose=-1,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=8, random_state=42,
        ),
        "LogisticRegression": LogisticRegression(
            max_iter=1000, random_state=42,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42,
        ),
    }

    results = []
    best_auc = -1.0
    best_name = ""
    best_estimator = None

    print("\n[4/6] Comparing 5 models (5-fold CV)â€¦")
    for name, model in models.items():
        t0 = time.time()
        cv_acc = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy", n_jobs=-1)
        model.fit(X_train, y_train)
        train_time = time.time() - t0

        t1 = time.time()
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        pred_time = (time.time() - t1) / max(len(X_test), 1)

        acc   = accuracy_score(y_test, y_pred)
        prec  = precision_score(y_test, y_pred, zero_division=0)
        rec   = recall_score(y_test, y_pred, zero_division=0)
        f1    = f1_score(y_test, y_pred, zero_division=0)
        auc   = roc_auc_score(y_test, y_prob)
        cv_m  = float(cv_acc.mean())

        results.append({
            "Model": name,
            "CV_Accuracy": cv_m,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "AUC_ROC": auc,
            "Train_Time_s": round(train_time, 2),
            "Pred_Time_us": round(pred_time * 1e6, 2),
        })

        if auc > best_auc:
            best_auc = auc
            best_name = name
            best_estimator = model

        print(
            f"  {name:<20}  CV={cv_m:.3f}  Acc={acc:.3f}  "
            f"F1={f1:.3f}  AUC={auc:.3f}  [{train_time:.1f}s]"
        )

    # Pretty table
    sep = "â”€"
    h = f"\n  â”Œ{'â”€'*22}â”¬{'â”€'*10}â”¬{'â”€'*8}â”¬{'â”€'*8}â”¬{'â”€'*10}â”"
    print(h)
    print(f"  â”‚ {'Model':<20} â”‚ {'Accuracy':>8} â”‚ {'F1':>6} â”‚ {'Recall':>6} â”‚ {'AUC-ROC':>8} â”‚")
    print(f"  â”œ{'â”€'*22}â”¼{'â”€'*10}â”¼{'â”€'*8}â”¼{'â”€'*8}â”¼{'â”€'*10}â”¤")
    for r in results:
        marker = " â˜…" if r["Model"] == best_name else "  "
        print(
            f"  â”‚ {r['Model']:<20} â”‚ {r['Accuracy']:>7.1%} "
            f"â”‚ {r['F1']:>6.3f} â”‚ {r['Recall']:>6.3f} â”‚ {r['AUC_ROC']:>8.4f} â”‚{marker}"
        )
    print(f"  â””{'â”€'*22}â”´{'â”€'*10}â”´{'â”€'*8}â”´{'â”€'*8}â”´{'â”€'*10}â”˜")
    print(f"\n  Best model: {best_name}  (AUC-ROC = {best_auc:.4f})")

    return best_name, best_estimator, results


# â”€â”€ Step 6 â€” Hyperparameter tuning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def tune_best_model(best_name: str, X_train, y_train):
    print(f"\n[5/6] Tuning {best_name} with RandomizedSearchCV (n_iter=50, cv=5)â€¦")

    if best_name == "XGBoost":
        base = XGBClassifier(eval_metric="logloss", random_state=42)
        param_dist = {
            "n_estimators": [200, 300, 400, 500],
            "max_depth": [3, 4, 5, 6, 7],
            "learning_rate": [0.01, 0.05, 0.1, 0.15],
            "subsample": [0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
            "min_child_weight": [1, 3, 5],
            "gamma": [0, 0.1, 0.2],
        }
    elif best_name == "LightGBM":
        base = LGBMClassifier(random_state=42, verbose=-1)
        param_dist = {
            "n_estimators": [200, 300, 400, 500],
            "max_depth": [3, 4, 5, 6, 7],
            "learning_rate": [0.01, 0.05, 0.1, 0.15],
            "num_leaves": [31, 63, 127],
            "subsample": [0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
        }
    elif best_name == "RandomForest":
        base = RandomForestClassifier(random_state=42)
        param_dist = {
            "n_estimators": [100, 200, 300, 400],
            "max_depth": [None, 6, 8, 10, 12],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
        }
    elif best_name == "GradientBoosting":
        base = GradientBoostingClassifier(random_state=42)
        param_dist = {
            "n_estimators": [100, 200, 300],
            "max_depth": [3, 4, 5],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.7, 0.8, 0.9, 1.0],
        }
    else:  # LogisticRegression or fallback
        base = LogisticRegression(random_state=42)
        param_dist = {
            "C": [0.01, 0.1, 1, 10, 100],
            "penalty": ["l1", "l2"],
            "solver": ["liblinear", "saga"],
            "max_iter": [500, 1000],
        }

    search = RandomizedSearchCV(
        base,
        param_dist,
        n_iter=50,
        cv=5,
        scoring="roc_auc",
        n_jobs=-1,
        random_state=42,
        verbose=1,
    )
    search.fit(X_train, y_train)
    print(f"  Best CV AUC-ROC: {search.best_score_:.4f}")
    print(f"  Best params: {search.best_params_}")
    return search.best_estimator_, search.best_params_, search.best_score_


# â”€â”€ Main pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    t_start = time.time()
    print("=" * 60)
    print("  LoanEase â€” Credit Underwriting Training Pipeline")
    print("=" * 60)

    # 1. Download
    download_datasets()

    # 2. Load + standardise
    print("\n[2/6] Loading and standardising datasetsâ€¦")
    dfs = []
    for name, path in [
        ("kaggle_loan",   str(DATA_DIR / "loan_train.csv")),
        ("uci_credit",    str(DATA_DIR / "uci_credit.csv")),
        ("german_credit", str(DATA_DIR / "german_credit.csv")),
        ("home_credit",   str(DATA_DIR / "home_credit_sample.csv")),
    ]:
        df = load_and_standardize(name, path)
        if not df.empty:
            df["_source"] = name
            dfs.append(df)

    if not dfs:
        print("ERROR: No datasets loaded. Aborting.")
        sys.exit(1)

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = df_all.drop(columns=["_source"])
    print(f"\n  Combined dataset: {len(df_all):,} rows Ã— {df_all.shape[1]} cols")
    print(f"  Class balance  : approved={int((df_all.target==1).sum())}  rejected={int((df_all.target==0).sum())}")

    # 3. Feature engineering
    print("\n[3/6] Engineering featuresâ€¦")
    df_all = engineer_features(df_all)

    X = df_all.drop("target", axis=1)
    y = df_all["target"].astype(int)

    # 3a. Build preprocessor and transform
    preprocessor, num_feats, cat_feats = build_preprocessor(X)
    X_proc = preprocessor.fit_transform(X)

    # Derive feature names
    ohe_cols = (
        preprocessor.named_transformers_["cat"]
        .named_steps["onehot"]
        .get_feature_names_out(cat_feats)
        .tolist()
    )
    feature_names = num_feats + ohe_cols

    # 3b. SMOTE
    print("  Applying SMOTE to balance classesâ€¦")
    smote = SMOTE(random_state=42)
    X_bal, y_bal = smote.fit_resample(X_proc, y)
    print(f"  After SMOTE: {X_bal.shape[0]:,} rows  "
          f"(approved={int((y_bal==1).sum())}  rejected={int((y_bal==0).sum())})")

    X_train, X_test, y_train, y_test = train_test_split(
        X_bal, y_bal, test_size=0.2, random_state=42, stratify=y_bal
    )
    print(f"  Train: {len(X_train):,}   Test: {len(X_test):,}")

    # 4. Model comparison
    best_name, _, comparison_results = compare_models(X_train, y_train, X_test, y_test)

    # 5. Hyperparameter tuning
    best_model, best_params, cv_score = tune_best_model(best_name, X_train, y_train)

    # Final evaluation
    print("\n[6/6] Final evaluation on held-out test setâ€¦")
    y_pred = best_model.predict(X_test)
    y_prob = best_model.predict_proba(X_test)[:, 1]
    test_accuracy = accuracy_score(y_test, y_pred)
    test_f1       = f1_score(y_test, y_pred, zero_division=0)
    test_auc      = roc_auc_score(y_test, y_prob)
    test_prec     = precision_score(y_test, y_pred, zero_division=0)
    test_rec      = recall_score(y_test, y_pred, zero_division=0)

    # 6. Save artifacts
    joblib.dump(best_model,   MODELS_DIR / "loan_model.pkl")
    joblib.dump(preprocessor, MODELS_DIR / "preprocessor.pkl")

    model_metadata = {
        "model_type": type(best_model).__name__,
        "training_date": datetime.now().isoformat(),
        "datasets_used": [
            "kaggle_loan_prediction",
            "uci_credit_approval",
            "german_credit",
            "home_credit_sample",
        ],
        "total_training_samples": int(len(X_train)),
        "total_dataset_rows": int(len(df_all)),
        "test_accuracy": round(test_accuracy, 4),
        "test_precision": round(test_prec, 4),
        "test_recall": round(test_rec, 4),
        "test_f1": round(test_f1, 4),
        "test_auc_roc": round(test_auc, 4),
        "feature_names": feature_names,
        "best_params": best_params,
        "cv_mean_score": round(float(cv_score), 4),
        "model_comparison": [
            {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
            for r in comparison_results
        ],
    }

    meta_path = MODELS_DIR / "model_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(model_metadata, f, indent=2)

    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"  Best model       : {best_name}")
    print(f"  Test Accuracy    : {test_accuracy:.4f}")
    print(f"  Test Precision   : {test_prec:.4f}")
    print(f"  Test Recall      : {test_rec:.4f}")
    print(f"  Test F1          : {test_f1:.4f}")
    print(f"  Test AUC-ROC     : {test_auc:.4f}")
    print(f"  CV AUC-ROC (best): {cv_score:.4f}")
    print(f"  Saved to         : {MODELS_DIR / 'loan_model.pkl'}")
    print(f"  Metadata         : {meta_path}")
    print(f"  Training complete in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

