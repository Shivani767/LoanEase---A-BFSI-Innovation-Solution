from __future__ import annotations

import json
from typing import Any


def _validate_number(value: Any, name: str) -> float:
    """Validate numeric input and return as float."""
    if value is None:
        raise ValueError(f"{name} is required")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, not bool")

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number") from exc

    return numeric


def classify_credit_score(score: float) -> str:
    """
    Classify credit score (0-900).

    0-300   -> High Risk (Low Score)
    301-699 -> Medium Risk (Intermediate Score)
    700-900 -> Low Risk (High Score)
    """
    score = _validate_number(score, "credit_score")
    if not 0 <= score <= 900:
        raise ValueError("credit_score must be between 0 and 900")

    if score <= 300:
        return "High Risk (Low Score)"
    if score <= 699:
        return "Medium Risk (Intermediate Score)"
    return "Low Risk (High Score)"


def classify_xgb_score(score: float) -> str:
    """
    Classify XGBoost risk score (0-100).

    0-33   -> Low Model Risk
    34-66  -> Medium Model Risk
    67-100 -> High Model Risk
    """
    score = _validate_number(score, "xgb_risk_score")
    if not 0 <= score <= 100:
        raise ValueError("xgb_risk_score must be between 0 and 100")

    if score <= 33:
        return "Low Model Risk"
    if score <= 66:
        return "Medium Model Risk"
    return "High Model Risk"


def get_final_risk(credit_category: str, model_category: str) -> str:
    """
    Combine credit category + model category into final risk.

    Rules:
    - If either side is High Risk -> High Risk
    - If both are Low Risk      -> Low Risk
    - Otherwise                 -> Medium Risk
    """
    if not credit_category or not model_category:
        raise ValueError("credit_category and model_category are required")

    credit_cat = str(credit_category).strip()
    model_cat = str(model_category).strip()

    credit_is_high = credit_cat.startswith("High Risk")
    model_is_high = model_cat.startswith("High")

    credit_is_low = credit_cat.startswith("Low Risk")
    model_is_low = model_cat.startswith("Low")

    if credit_is_high or model_is_high:
        return "High Risk"
    if credit_is_low and model_is_low:
        return "Low Risk"
    return "Medium Risk"


def assign_interest_rate(final_risk: str) -> dict[str, float]:
    """
    Assign interest range by final risk category.

    All users remain eligible; risk affects pricing only.
    """
    if not final_risk:
        raise ValueError("final_risk is required")

    risk = str(final_risk).strip()

    rate_table: dict[str, tuple[float, float]] = {
        "High Risk": (13.0, 15.0),
        "Medium Risk": (11.0, 13.0),
        "Low Risk": (9.0, 11.0),
    }

    if risk not in rate_table:
        raise ValueError(f"Unsupported final_risk: {risk}")

    min_rate, max_rate = rate_table[risk]
    suggested_rate = round((min_rate + max_rate) / 2, 2)

    return {
        "min_rate": min_rate,
        "max_rate": max_rate,
        "suggested_rate": suggested_rate,
    }


def evaluate_applicant(credit_score: float, xgb_risk_score: float) -> dict[str, Any]:
    """Return complete structured decision payload for loan pricing."""
    credit_category = classify_credit_score(credit_score)
    model_category = classify_xgb_score(xgb_risk_score)
    final_risk = get_final_risk(credit_category, model_category)
    pricing = assign_interest_rate(final_risk)

    return {
        "input": {
            "credit_score": float(credit_score),
            "xgb_risk_score": float(xgb_risk_score),
        },
        "classification": {
            "credit_category": credit_category,
            "model_category": model_category,
            "final_risk": final_risk,
        },
        "loan_decision": {
            "eligible": True,
            "interest_rate_range": {
                "min": pricing["min_rate"],
                "max": pricing["max_rate"],
            },
            "suggested_interest_rate": pricing["suggested_rate"],
        },
    }


def main() -> None:
    """Sample test cases."""
    samples = [
        {"credit_score": 280, "xgb_risk_score": 25},
        {"credit_score": 620, "xgb_risk_score": 50},
        {"credit_score": 790, "xgb_risk_score": 20},
        {"credit_score": 740, "xgb_risk_score": 72},
    ]

    for i, sample in enumerate(samples, start=1):
        result = evaluate_applicant(sample["credit_score"], sample["xgb_risk_score"])
        print(f"\nCase {i}")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
