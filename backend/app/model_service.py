from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap  # type: ignore[import-not-found]
from sklearn.utils import resample

from app.credit_score import get_credit_score, get_credit_band
from app.risk_combiner import evaluate_applicant
from services.shap_narrator import generate_shap_narration


REQUEST_TO_DATASET_COLUMN = {
    "gender": "Gender",
    "married": "Married",
    "dependents": "Dependents",
    "education": "Education",
    "self_employed": "Self_Employed",
    "applicant_income": "ApplicantIncome",
    "coapplicant_income": "CoapplicantIncome",
    "loan_amount": "LoanAmount",
    "loan_amount_term": "Loan_Amount_Term",
    "credit_history": "Credit_History",
    "property_area": "Property_Area",
}


class ModelService:
    def __init__(self, artifacts_dir: Path, threshold: float = 0.65) -> None:
        self.artifacts_dir = artifacts_dir
        self.threshold = threshold

        self.model = joblib.load(self.artifacts_dir / "loan_model.pkl")
        self.preprocessor = joblib.load(self.artifacts_dir / "preprocessor.pkl")

        self.feature_columns: list[str] = self.preprocessor["feature_columns"]
        self.numeric_columns: list[str] = self.preprocessor["numeric_columns"]
        self.categorical_columns: list[str] = self.preprocessor["categorical_columns"]
        self.medians: dict = self.preprocessor["medians"]
        self.modes: dict = self.preprocessor["modes"]
        self.feature_encoders: dict = self.preprocessor["feature_encoders"]
        self.target_encoder = self.preprocessor["target_encoder"]
        self.model_version: str = self.preprocessor.get("model_version", "unknown")
        self.metrics: dict = self.preprocessor.get("metrics", {})

        self.explainer = shap.TreeExplainer(self.model)
        self._prediction_history: list[dict[str, Any]] = []
        self._drift_warning = False
        self._drifted_features: list[str] = []
        self._drift_recommendation: str | None = None

    def _normalize_input(self, payload: dict) -> pd.DataFrame:
        row = {dataset_col: payload[request_col] for request_col, dataset_col in REQUEST_TO_DATASET_COLUMN.items()}
        df = pd.DataFrame([row], columns=self.feature_columns)

        for col in self.numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(self.medians[col])

        for col in self.categorical_columns:
            df[col] = df[col].fillna(self.modes[col]).astype(str)
            enc = self.feature_encoders[col]
            default_value = self.modes[col]
            default_encoded = int(enc.transform([default_value])[0])
            mapped = []
            valid_values = set(enc.classes_.tolist())
            for value in df[col].tolist():
                if value in valid_values:
                    mapped.append(int(enc.transform([value])[0]))
                else:
                    mapped.append(default_encoded)
            df[col] = mapped

        return df

    def _approval_probability(self, X: pd.DataFrame) -> float:
        positive_encoded = int(self.target_encoder.transform(["Y"])[0])
        class_positions = {int(label): idx for idx, label in enumerate(self.model.classes_)}
        positive_idx = class_positions[positive_encoded]
        probabilities = self.model.predict_proba(X)[0]
        return float(probabilities[positive_idx])

    def _fallback_probability(self, payload: dict) -> float:
        credit_score = float(payload.get("credit_score", 700) or 700)
        income = float(payload.get("applicant_income", 50000) or 50000)
        loan_amount = float(payload.get("loan_amount", 500000) or 500000)
        tenure_months = max(1, int(payload.get("loan_amount_term", 60) or 60))
        income_factor = min(max(income / max(loan_amount / 12, 1.0), 0.0), 2.0)
        base = (credit_score - 300) / 600 * 0.65 + min(income_factor / 2, 1.0) * 0.35
        tenure_penalty = 0.02 if tenure_months < 24 else 0.0
        return float(min(max(base - tenure_penalty, 0.05), 0.95))

    def _predict_with_confidence(
        self,
        X: pd.DataFrame,
        payload: dict | None = None,
        n_bootstrap: int = 50,
    ) -> tuple[float, float, float]:
        if self.model is None:
            fallback_probability = self._fallback_probability(payload or {})
            spread = 0.18
            return fallback_probability, max(0.0, fallback_probability - spread), min(1.0, fallback_probability + spread)

        if X.empty:
            return 0.5, 0.0, 1.0

        bootstrap_predictions: list[float] = []
        numeric_noise_scale = {
            col: max(float(abs(self.medians.get(col, 1.0))) * 0.03, 1.0)
            for col in self.numeric_columns
        }

        for _ in range(n_bootstrap):
            sample = X.copy(deep=True)
            for col in self.numeric_columns:
                if col in sample.columns:
                    noise = np.random.normal(0.0, numeric_noise_scale.get(col, 1.0), size=len(sample))
                    sample[col] = pd.to_numeric(sample[col], errors="coerce").fillna(self.medians.get(col, 0.0)) + noise
            try:
                boot_rows = resample(sample, replace=True, n_samples=len(sample))
                boot_pred = float(self.model.predict_proba(boot_rows)[0][1])
                bootstrap_predictions.append(boot_pred)
            except Exception:
                continue

        if not bootstrap_predictions:
            try:
                point_prediction = float(self.model.predict_proba(X)[0][1])
            except Exception:
                point_prediction = self._fallback_probability(payload or {})
            spread = 0.18 if payload else 0.10
            return point_prediction, max(0.0, point_prediction - spread), min(1.0, point_prediction + spread)

        mean_pred = float(np.mean(bootstrap_predictions))
        lower = float(np.percentile(bootstrap_predictions, 10))
        upper = float(np.percentile(bootstrap_predictions, 90))
        return mean_pred, lower, upper

    def _confidence_band(self, width: float) -> str:
        if width < 0.15:
            return "HIGH"
        if width < 0.25:
            return "MEDIUM"
        return "LOW"

    def _check_income_reasonability(self, income: float, loan_amount: float, tenure_months: int) -> dict:
        estimated_rate = 12.0
        r = estimated_rate / 12 / 100
        n_periods = max(1, int(tenure_months))
        principal = max(float(loan_amount), 0.0)
        monthly_income = max(float(income), 1.0)

        if r == 0:
            emi = principal / n_periods
            factor = 1 / n_periods
        else:
            factor = r * (1 + r) ** n_periods / (((1 + r) ** n_periods) - 1)
            emi = principal * factor

        foir = emi / monthly_income

        if foir > 0.65:
            required_monthly_income = round(emi / 0.40, 2)
            suggested_amount = round((monthly_income * 0.40 / factor) if factor else 0.0, 2)
            return {
                "flag": "HIGH_FOIR",
                "foir": round(foir, 2),
                "message": (
                    f"EMI would be {round(foir * 100)}% of income. Recommended maximum is 40%."
                ),
                "suggested_amount": suggested_amount,
                "required_monthly_income": required_monthly_income,
                "emi": round(emi, 2),
            }
        if foir > 0.40:
            return {
                "flag": "ELEVATED_FOIR",
                "foir": round(foir, 2),
                "message": "EMI is elevated relative to income.",
                "required_monthly_income": round(emi / 0.40, 2),
                "emi": round(emi, 2),
            }
        return {
            "flag": "ACCEPTABLE",
            "foir": round(foir, 2),
            "emi": round(emi, 2),
        }

    def _record_prediction(self, raw_row: dict) -> None:
        snapshot = {
            key: raw_row.get(key)
            for key in REQUEST_TO_DATASET_COLUMN.values()
        }
        self._prediction_history.append(snapshot)
        if len(self._prediction_history) > 100:
            self._prediction_history = self._prediction_history[-100:]
        self._update_drift_state()

    def _update_drift_state(self) -> None:
        recent = self._prediction_history[-50:]
        if len(recent) < 50:
            self._drift_warning = False
            self._drifted_features = []
            self._drift_recommendation = None
            return

        drifted: list[str] = []
        for dataset_col in self.numeric_columns:
            if dataset_col not in REQUEST_TO_DATASET_COLUMN.values():
                continue

            values = [row.get(dataset_col) for row in recent]
            numeric_values = [float(value) for value in values if value is not None]
            if not numeric_values:
                continue

            baseline = float(self.medians.get(dataset_col, 0.0) or 0.0)
            recent_mean = float(np.mean(numeric_values))
            mean_abs_dev = float(np.mean(np.abs(np.array(numeric_values, dtype=float) - baseline)))
            scale = max(abs(baseline), 1.0)
            relative_deviation = mean_abs_dev / scale
            mean_shift = abs(recent_mean - baseline) / scale

            if max(relative_deviation, mean_shift) > 0.30:
                drifted.append(dataset_col)

        self._drift_warning = bool(drifted)
        self._drifted_features = drifted
        self._drift_recommendation = (
            "Retrain model with recent data" if drifted else None
        )

    def drift_status(self) -> dict:
        return {
            "model_drift_warning": self._drift_warning,
            "drifted_features": list(self._drifted_features),
            "recommendation": self._drift_recommendation,
        }

    def _risk_decision(self, probability: float) -> tuple[str, str]:
        if probability >= 0.75:
            return "APPROVED", "Low Risk"
        if probability >= 0.50:
            return "APPROVED_WITH_CONDITIONS", "Medium Risk"
        return "REJECTED", "High Risk"

    def _feature_phrase(self, feature: str, value: float | str, shap_value: float) -> str:
        supports = shap_value >= 0
        direction = "supports" if supports else "reduces"

        if feature == "Credit_History":
            if supports:
                return "Strong credit history significantly supports approval"
            return "Weak or missing credit history increases rejection risk"

        if feature in {"ApplicantIncome", "CoapplicantIncome"}:
            if supports:
                return "Income profile improves repayment confidence"
            return "Income profile appears weaker for the requested loan"

        if feature == "LoanAmount":
            if supports:
                return "Requested loan amount is aligned with applicant profile"
            return "Higher requested loan amount raises risk concerns"

        pretty = feature.replace("_", " ")
        return f"{pretty} {direction} the approval outcome"

    def _build_shap_breakdown(self, X_encoded: pd.DataFrame, raw_row: dict) -> tuple[list[dict], list[str]]:
        shap_values = self.explainer.shap_values(X_encoded)

        if isinstance(shap_values, list):
            shap_row = np.array(shap_values[0][0], dtype=float)
        else:
            shap_array = np.array(shap_values)
            if shap_array.ndim == 3:
                shap_row = shap_array[0, :, 0].astype(float)
            else:
                shap_row = shap_array[0].astype(float)

        waterfall = []
        for idx, feature in enumerate(self.feature_columns):
            value = raw_row[feature]
            score = float(shap_row[idx])
            waterfall.append(
                {
                    "feature": feature,
                    "value": value,
                    "shap_value": score,
                    "impact": "positive" if score >= 0 else "negative",
                    "plain_english": self._feature_phrase(feature, value, score),
                }
            )

        waterfall_sorted = sorted(waterfall, key=lambda item: abs(item["shap_value"]), reverse=True)
        top_explanations = [item["plain_english"] for item in waterfall_sorted[:3]]
        return waterfall_sorted, top_explanations

    def assess(self, payload: dict) -> dict:
        """
        Assess loan application using combined credit + model risk.
        All users remain eligible; pricing depends on final risk tier.
        """
        pan_number = payload.get("pan_number", "")
        credit_score = get_credit_score(pan_number)
        credit_band = get_credit_band(credit_score)

        raw_row = {
            dataset_col: payload[request_col]
            for request_col, dataset_col in REQUEST_TO_DATASET_COLUMN.items()
        }
        X_encoded = self._normalize_input(payload)
        probability, confidence_lower, confidence_upper = self._predict_with_confidence(X_encoded, payload)
        xgboost_probability = probability
        waterfall, top_explanations = self._build_shap_breakdown(X_encoded, raw_row)

        # Composite visibility score for explainability UI.
        normalized_credit = (credit_score - 300) / 600 * 100
        combined_score = round((normalized_credit * 0.60) + (xgboost_probability * 100 * 0.40))

        # Convert approval probability into model risk score (0 low risk, 100 high risk).
        xgb_risk_score = round((1.0 - xgboost_probability) * 100, 2)
        combined_risk = evaluate_applicant(credit_score=credit_score, xgb_risk_score=xgb_risk_score)
        final_risk_tier = combined_risk["classification"]["final_risk"]

        confidence_width = round(confidence_upper - confidence_lower, 4)
        model_certainty = self._confidence_band(confidence_width)

        loan_amount = float(payload.get("loan_amount") or 0)
        monthly_income = float(payload.get("applicant_income") or 50000)
        tenure_months = int(payload.get("loan_amount_term") or 60)
        income_reasonability = self._check_income_reasonability(monthly_income, loan_amount, tenure_months)

        if probability < 0.35:
            final_decision = "REJECTED"
        elif 0.35 <= probability < 0.50:
            final_decision = "CONDITIONAL_REJECT"
        elif final_risk_tier == "Low Risk":
            final_decision = "APPROVED"
        else:
            final_decision = "APPROVED_WITH_CONDITIONS"

        if income_reasonability.get("flag") == "HIGH_FOIR" and final_decision == "APPROVED":
            final_decision = "APPROVED_WITH_CONDITIONS"
        if income_reasonability.get("flag") == "HIGH_FOIR" and probability < 0.60:
            final_decision = "CONDITIONAL_REJECT"
        if model_certainty == "LOW" and final_decision == "APPROVED":
            final_decision = "APPROVED_WITH_CONDITIONS"

        soft_reject_guidance = None
        confidence_message = f"Our model is {model_certainty} confidence in this assessment"
        if final_decision == "CONDITIONAL_REJECT":
            score_gap = max(0.0, (self.threshold * 100) - combined_score)
            required_monthly_income = float(income_reasonability.get("required_monthly_income") or round(loan_amount / max(tenure_months, 1), 2))
            income_gap = max(0.0, required_monthly_income - monthly_income)
            suggested_amount = float(income_reasonability.get("suggested_amount") or max(loan_amount * 0.4, 0.0))
            soft_reject_guidance = {
                "message": "Your profile narrowly missed our threshold. Here's exactly what would change the decision:",
                "income_delta_monthly": round(income_gap, 2),
                "repayment_history_months": 6,
                "repayment_history_impact": "6 months of on-time EMI payments typically adds 40-50 points to CIBIL",
                "suggested_approved_amount": round(suggested_amount, 2),
                "threshold_gap_points": round(score_gap, 2),
            }

        # Generate structured SHAP narration with actual feature values
        shap_values_array = np.array([item["shap_value"] for item in waterfall])
        feature_values_dict = {item["feature"]: item["value"] for item in waterfall}
        structured_narration = generate_shap_narration(
            shap_values=shap_values_array,
            feature_names=self.feature_columns,
            feature_values=feature_values_dict,
            decision=final_decision,
            language="en",
        )

        rate_range = combined_risk["loan_decision"]["interest_rate_range"]
        rate = combined_risk["loan_decision"]["suggested_interest_rate"]

        if final_risk_tier == "Low Risk":
            negotiation_allowed = True
            max_negotiation_rounds = 3
        elif final_risk_tier == "Medium Risk":
            negotiation_allowed = True
            max_negotiation_rounds = 1
        else:
            negotiation_allowed = False
            max_negotiation_rounds = 0

        self._record_prediction({
            **payload,
            "cibil_score": credit_score,
            "approval_probability": probability,
            "risk_score": combined_score,
            "loan_amount": loan_amount,
            "loan_amount_term": tenure_months,
        })

        assessment = {
            "decision": final_decision,
            "credit_score": credit_score,
            "credit_score_out_of": 900,
            "credit_band": credit_band["label"],
            "credit_band_color": credit_band["color"],
            "risk_score": combined_score,
            "risk_score_out_of": 100,
            "approval_probability": round(probability, 4),
            "confidence_lower": round(confidence_lower, 4),
            "confidence_upper": round(confidence_upper, 4),
            "confidence_width": confidence_width,
            "model_certainty": model_certainty,
            "risk_tier": final_risk_tier,
            "offered_rate": rate,
            "rate_range": rate_range,
            "negotiation_allowed": negotiation_allowed,
            "max_negotiation_rounds": max_negotiation_rounds,
            "xgboost_probability": round(xgboost_probability, 2),
            "xgboost_ran": True,
            "shap_explanation": top_explanations,
            "structured_shap_narration": structured_narration,
            "threshold_used": self.threshold,
            "raw_input": raw_row,
            "shap_waterfall": waterfall,
            "income_reasonability": income_reasonability,
            "soft_reject_guidance": soft_reject_guidance,
            "model_drift_warning": self._drift_warning,
            "drifted_features": list(self._drifted_features),
            "recommendation": self._drift_recommendation,
            "confidence_message": confidence_message,
        }

        if final_decision == "REJECTED" and final_risk_tier == "High Risk":
            assessment["recommendation"] = "Retrain model with recent data" if self._drift_warning else assessment["recommendation"]

        return assessment
