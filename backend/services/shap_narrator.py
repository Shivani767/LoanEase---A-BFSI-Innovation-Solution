from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd


FEATURE_LABEL_MAP: dict[str, str] = {
    "cibil_score": "CIBIL credit score",
    "monthly_income": "monthly income",
    "annual_income": "annual income",
    "loan_amount": "requested loan amount",
    "loan_to_income": "loan amount relative to income",
    "foir": "existing EMI burden (FOIR)",
    "dti": "debt-to-income ratio",
    "tenure": "loan tenure (months)",
    "tenure_months": "loan tenure (months)",
    "interest_rate": "interest rate expectation",
    "delinquency_count": "missed payments in the past",
    "account_age_months": "length of credit history",
    "credit_history": "repayment history quality",
    "open_accounts": "number of active credit lines",
    "secured_loan_ratio": "share of secured loans",
    "credit_utilization": "credit card utilization",
    "recent_inquiries": "recent credit inquiries",
    "employment_years": "years in current employment",
    "emp_type_A": "employment type (self-employed)",
    "emp_type_B": "employment type (salaried)",
    "emp_type_C": "employment type (business owner)",
    "residence_stability_months": "residence stability",
    "savings_balance": "average savings balance",
    "emi_obligations": "current EMI obligations",
    "coapplicant_income": "co-applicant income",
    "property_area_Urban": "property area (urban)",
    "property_area_Semiurban": "property area (semi-urban)",
    "property_area_Rural": "property area (rural)",
    "self_employed_Yes": "self-employed status",
    "education_Graduate": "education level (graduate)",
}

# Bilingual feature labels for structured narration
FEATURE_LABELS: dict[str, dict[str, str]] = {
    "Credit_History": {
        "en": "your credit repayment history",
        "hi": "आपकी credit repayment history"
    },
    "ApplicantIncome": {
        "en": "your monthly income",
        "hi": "आपकी monthly income"
    },
    "LoanAmount": {
        "en": "your requested loan amount",
        "hi": "आपकी loan राशि"
    },
    "Loan_Amount_Term": {
        "en": "your chosen loan tenure",
        "hi": "आपकी loan अवधि"
    },
    "CoapplicantIncome": {
        "en": "your co-applicant's income",
        "hi": "आपके co-applicant की income"
    },
    "Property_Area": {
        "en": "your property location",
        "hi": "आपकी property का location"
    },
    "Gender": {
        "en": "your gender",
        "hi": "आपका gender"
    },
    "Married": {
        "en": "your marital status",
        "hi": "आपकी marital status"
    },
    "Dependents": {
        "en": "your number of dependents",
        "hi": "आपके dependents"
    },
    "Education": {
        "en": "your education level",
        "hi": "आपकी education"
    },
    "Self_Employed": {
        "en": "your employment type",
        "hi": "आपका employment type"
    },
}

ACTIONABLE_FEATURES: list[str] = [
    "cibil_score",
    "monthly_income",
    "foir",
    "loan_amount",
    "tenure",
]

_ACTIONABLE_BOUNDS: dict[str, Tuple[float, float]] = {
    "cibil_score": (300.0, 900.0),
    "monthly_income": (5000.0, 2_000_000.0),
    "foir": (0.0, 100.0),
    "loan_amount": (10_000.0, 100_000_000.0),
    "tenure": (6.0, 480.0),
}

_ACTIONABLE_STEPS: dict[str, Iterable[float]] = {
    "cibil_score": [10, 20, 30, 40, 50, 70, 100],
    "monthly_income": [5000, 10000, 20000, 30000, 50000, 75000, 100000],
    "foir": [2, 4, 6, 8, 10, 12, 15],
    "loan_amount": [25000, 50000, 100000, 200000, 300000, 500000, 750000],
    "tenure": [6, 12, 18, 24, 36, 48, 60],
}


@dataclass
class _CandidateChange:
    feature: str
    original: float
    updated: float
    delta: float
    score_after: float


def _human_label(feature_name: str) -> str:
    return FEATURE_LABEL_MAP.get(feature_name, feature_name.replace("_", " "))


def _bilingual_label(feature_name: str, language: str = "en") -> str:
    """Get bilingual label for a feature. Falls back to human_label."""
    labels = FEATURE_LABELS.get(feature_name, {})
    return labels.get(language, labels.get("en", _human_label(feature_name)))


def format_shap_for_prompt(shap_values: dict[str, float], top_n: int = 5) -> str:
    """Format top-N SHAP contributors into a prompt-ready numbered list."""
    if not shap_values:
        return "1. Feature: data unavailable, Direction: neutral, Magnitude: 0.00"

    ranked = sorted(
        shap_values.items(),
        key=lambda kv: abs(float(kv[1])),
        reverse=True,
    )[: max(1, top_n)]

    lines: list[str] = []
    for idx, (feature, raw_value) in enumerate(ranked, start=1):
        value = float(raw_value)
        direction = "positive" if value >= 0 else "negative"
        lines.append(
            f"{idx}. Feature: {_human_label(feature)}, Direction: {direction}, Magnitude: {abs(value):.2f}"
        )
    return "\n".join(lines)


def generate_shap_narration(
    shap_values: np.ndarray,
    feature_names: list[str],
    feature_values: dict[str, Any],
    decision: str,
    language: str = "en",
    threshold: float = 0.05,
) -> dict[str, Any]:
    """
    Generate structured SHAP narration that references actual feature values.

    Args:
        shap_values: Array of SHAP values for each feature.
        feature_names: List of feature names corresponding to shap_values.
        feature_values: Dict mapping feature names to their actual values.
        decision: The model decision (APPROVED, APPROVED_WITH_CONDITIONS, REJECTED).
        language: "en" or "hi".
        threshold: Minimum absolute SHAP value to consider a factor significant.

    Returns:
        Structured narration dict with summary, factors, primary_reason, and tips.
    """
    # Sort features by absolute SHAP value
    importance = sorted(
        zip(
            feature_names,
            shap_values,
            [feature_values.get(f, "N/A") for f in feature_names],
        ),
        key=lambda x: abs(float(x[1])),
        reverse=True,
    )

    # Separate positive and negative factors
    positive_factors = [
        (name, float(val), actual)
        for name, val, actual in importance
        if float(val) > threshold
    ]
    negative_factors = [
        (name, float(val), actual)
        for name, val, actual in importance
        if float(val) < -threshold
    ]

    # Build structured narration
    narration: dict[str, Any] = {
        "summary": "",
        "positive_factors": [],
        "negative_factors": [],
        "primary_reason": "",
        "improvement_tips": [],
        "decision": decision,
        "language": language,
    }

    # Build factor lists with bilingual labels and actual values
    for name, val, actual in positive_factors[:3]:
        label = _bilingual_label(name, language)
        narration["positive_factors"].append({
            "feature": name,
            "label": label,
            "shap_value": round(val, 3),
            "actual_value": actual,
        })

    for name, val, actual in negative_factors[:3]:
        label = _bilingual_label(name, language)
        narration["negative_factors"].append({
            "feature": name,
            "label": label,
            "shap_value": round(val, 3),
            "actual_value": actual,
        })

    # Top positive factor with actual value as primary reason
    if positive_factors:
        top_pos = positive_factors[0]
        label = _bilingual_label(top_pos[0], language)
        actual_val = top_pos[2]
        if language == "hi":
            narration["primary_reason"] = (
                f"{label} (₹{actual_val}) ने सबसे ज्यादा "
                f"आपके approval में मदद की।"
            )
        else:
            narration["primary_reason"] = (
                f"{label} (value: {actual_val}) was the strongest "
                f"factor supporting your approval."
            )

    # Top negative factor as concern
    if negative_factors:
        top_neg = negative_factors[0]
        label = _bilingual_label(top_neg[0], language)
        actual_val = top_neg[2]
        if language == "hi":
            concern = (
                f"{label} (₹{actual_val}) ने approval chances को "
                f"थोड़ा कम किया।"
            )
        else:
            concern = (
                f"{label} (value: {actual_val}) reduced your "
                f"approval chances."
            )
        narration["primary_concern"] = concern

    # Summary based on decision
    if decision == "APPROVED":
        if language == "hi":
            narration["summary"] = (
                f"आपका loan approve हो गया है। "
                f"{len(positive_factors)} factors ने आपके favour में काम किया।"
            )
        else:
            narration["summary"] = (
                f"Your loan is approved. "
                f"{len(positive_factors)} factors worked in your favour."
            )
    elif decision == "APPROVED_WITH_CONDITIONS":
        if language == "hi":
            narration["summary"] = (
                f"आपका loan conditions के साथ approve हुआ है। "
                f"{len(positive_factors)} positive और {len(negative_factors)} negative factors मिले।"
            )
        else:
            narration["summary"] = (
                f"Your loan is approved with conditions. "
                f"We found {len(positive_factors)} positive and {len(negative_factors)} negative factors."
            )
    else:
        if language == "hi":
            narration["summary"] = (
                f"अभी के लिए loan eligible नहीं। "
                f"{len(negative_factors)} factors ने approval में रुकावट डाली।"
            )
        else:
            narration["summary"] = (
                f"Unfortunately, the loan is not approved at this time. "
                f"{len(negative_factors)} factors held back the approval."
            )

    # Improvement tips based on negative factors
    for name, val, actual in negative_factors[:2]:
        if name == "Credit_History":
            tip = (
                "Timely EMI payments अगले 6 months करें — "
                if language == "hi" else
                "Make timely EMI payments for the next 6 months — "
            )
            tip += "this will improve your CIBIL score."
            narration["improvement_tips"].append(tip)
        elif name in {"ApplicantIncome", "CoapplicantIncome"}:
            tip = (
                "Income proof जैसे salary slips या ITR submit करें — "
                if language == "hi" else
                "Submit income proof like salary slips or ITR — "
            )
            tip += "higher documented income strengthens your profile."
            narration["improvement_tips"].append(tip)
        elif name == "LoanAmount":
            tip = (
                "Thoda kam loan amount request करें — "
                if language == "hi" else
                "Request a slightly lower loan amount — "
            )
            tip += "this improves your debt-to-income ratio."
            narration["improvement_tips"].append(tip)
        elif name == "Loan_Amount_Term":
            tip = (
                "Longer tenure choose करें — "
                if language == "hi" else
                "Choose a longer tenure — "
            )
            tip += "this reduces your monthly EMI burden."
            narration["improvement_tips"].append(tip)

    if not narration["improvement_tips"]:
        if language == "hi":
            narration["improvement_tips"].append(
                "CIBIL score improve करें और existing debts कम करें।"
            )
        else:
            narration["improvement_tips"].append(
                "Work on improving your CIBIL score and reducing existing debts."
            )

    return narration


def format_structured_shap_for_groq(narration: dict[str, Any]) -> str:
    """Serialize structured SHAP narration into a Groq prompt-ready string."""
    lines: list[str] = []
    lines.append(f"Decision: {narration.get('decision', 'N/A')}")
    lines.append(f"Summary: {narration.get('summary', '')}")
    lines.append(f"Primary Reason: {narration.get('primary_reason', '')}")

    if narration.get("primary_concern"):
        lines.append(f"Primary Concern: {narration['primary_concern']}")

    lines.append("\nTop Positive Factors (helped approval):")
    for factor in narration.get("positive_factors", []):
        lines.append(
            f"  - {factor['label']}: SHAP={factor['shap_value']:.3f}, "
            f"Actual Value={factor['actual_value']}"
        )

    lines.append("\nTop Negative Factors (hurt chances):")
    for factor in narration.get("negative_factors", []):
        lines.append(
            f"  - {factor['label']}: SHAP={factor['shap_value']:.3f}, "
            f"Actual Value={factor['actual_value']}"
        )

    lines.append("\nImprovement Tips:")
    for tip in narration.get("improvement_tips", []):
        lines.append(f"  - {tip}")

    return "\n".join(lines)


def _score_profile(model: Any, profile: dict[str, Any]) -> float:
    """
    Compute approval probability for a single profile.

    Supports models with either `predict_proba` or `predict`.
    """
    frame = pd.DataFrame([profile])
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(frame)
        # Binary classifier assumed; use probability of positive class.
        return float(proba[0][1]) if np.ndim(proba) > 1 else float(proba[0])

    pred = model.predict(frame)
    return float(pred[0])


def _preferred_direction(feature: str, favor_approval: bool) -> int:
    """
    Direction for actionable movement.
    +1 means increase, -1 means decrease.
    """
    if feature in {"cibil_score", "monthly_income", "tenure"}:
        return 1 if favor_approval else -1
    if feature in {"foir", "loan_amount"}:
        return -1 if favor_approval else 1
    return 1


def _bounded(value: float, feature: str) -> float:
    low, high = _ACTIONABLE_BOUNDS[feature]
    return float(min(max(value, low), high))


def generate_counterfactual(shap_values: dict, profile: dict, model: Any) -> str:
    """
    Find the smallest actionable feature change likely to flip the model decision.
    """
    if not profile or model is None:
        return "Counterfactual unavailable: profile or model is missing."

    score_now = _score_profile(model, profile)
    current_label = 1 if score_now >= 0.5 else 0

    # Primary use-case is helping a rejected applicant qualify.
    if current_label == 1:
        return (
            "Applicant is already likely approved. To improve terms further, reduce FOIR or request a slightly lower loan amount."
        )

    best: _CandidateChange | None = None
    target_label = 1

    for feature in ACTIONABLE_FEATURES:
        if feature not in profile:
            continue
        try:
            base = float(profile[feature])
        except (TypeError, ValueError):
            continue

        direction = _preferred_direction(feature, favor_approval=True)
        for step in _ACTIONABLE_STEPS[feature]:
            candidate_value = _bounded(base + (direction * float(step)), feature)
            if candidate_value == base:
                continue

            candidate_profile = dict(profile)
            candidate_profile[feature] = candidate_value
            score_after = _score_profile(model, candidate_profile)
            label_after = 1 if score_after >= 0.5 else 0

            if label_after != target_label:
                continue

            delta = abs(candidate_value - base)
            if best is None or delta < best.delta:
                best = _CandidateChange(
                    feature=feature,
                    original=base,
                    updated=candidate_value,
                    delta=delta,
                    score_after=score_after,
                )

    if best is None:
        return (
            "No single actionable change was sufficient to flip the decision. A combined improvement in CIBIL score and FOIR is recommended."
        )

    feature_label = _human_label(best.feature)
    if best.feature == "loan_amount":
        return (
            f"If your {feature_label} were {int(best.updated):,} instead of {int(best.original):,}, "
            "the model indicates your approval chances would likely cross the threshold."
        )
    if best.feature == "monthly_income":
        return (
            f"If your {feature_label} were {int(best.updated):,} instead of {int(best.original):,}, "
            "you would likely qualify for a stronger approval outcome."
        )
    return (
        f"If your {feature_label} were {best.updated:.0f} instead of {best.original:.0f}, "
        "the decision would likely flip to approved."
    )


def _profile_summary(profile: dict[str, Any]) -> str:
    if not profile:
        return "No applicant profile details available."
    keys_of_interest = [
        "cibil_score",
        "monthly_income",
        "loan_amount",
        "foir",
        "tenure",
        "employment_type",
    ]
    parts: list[str] = []
    for key in keys_of_interest:
        if key in profile:
            parts.append(f"{_human_label(key)}: {profile[key]}")
    if not parts:
        for key, value in list(profile.items())[:6]:
            parts.append(f"{_human_label(key)}: {value}")
    return "; ".join(parts)


def build_shap_context_for_prompt(
    shap_values: dict,
    decision: str,
    profile: dict,
    model: Any,
) -> dict:
    """Build prompt context block for UNDERWRITING_SYSTEM_PROMPT injection."""
    credit_score = profile.get("cibil_score") or profile.get("credit_score")
    return {
        "shap_summary": format_shap_for_prompt(shap_values, top_n=5),
        "counterfactual": generate_counterfactual(shap_values, profile, model),
        "decision": decision,
        "credit_score": credit_score,
        "profile_summary": _profile_summary(profile),
    }

