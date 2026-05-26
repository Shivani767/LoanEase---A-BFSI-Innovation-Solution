"""
Credit score simulation and banding for LoanEase underwriting.
Deterministic bureau score tied to PAN number as simulation of CIBIL.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal


# Demo PAN scores: hardcoded for predictable demo behavior
DEMO_PAN_SCORES = {
    "ABCDE1234F": 820,  # High score — easy approval
    "XYZPQ5678K": 680,  # Medium score — conditional
    "LMNOP9012R": 420,  # Low score — likely rejection
    "QRSTU3456S": 285,  # Below cutoff — hard reject
    "DEMO00000D": 750,  # Safe demo score
}


# Credit score bands for pricing (all applicants remain eligible)
CREDIT_SCORE_BANDS = {
    "HIGH_RISK_LOW_SCORE": {
        "min": 0,
        "max": 300,
        "label": "High Risk (Low Score)",
        "color": "red",
        "eligible": True,
        "rate_min": 13.0,
        "rate_max": 15.0,
        "xgboost_runs": True,
        "negotiation_allowed": False,
        "max_negotiation_rounds": 0,
    },
    "MEDIUM_RISK_INTERMEDIATE": {
        "min": 301,
        "max": 699,
        "label": "Medium Risk (Intermediate Score)",
        "color": "yellow",
        "eligible": True,
        "rate_min": 11.0,
        "rate_max": 13.0,
        "xgboost_runs": True,
        "negotiation_allowed": True,
        "max_negotiation_rounds": 1,
    },
    "LOW_RISK_HIGH_SCORE": {
        "min": 700,
        "max": 900,
        "label": "Low Risk (High Score)",
        "color": "green",
        "eligible": True,
        "rate_min": 9.0,
        "rate_max": 11.0,
        "xgboost_runs": True,
        "negotiation_allowed": True,
        "max_negotiation_rounds": 3,
    },
}


def validate_pan(pan: str) -> bool:
    """Validate PAN format: 5 letters, 4 digits, 1 letter."""
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan))


def simulate_credit_score(pan: str) -> int:
    """
    Generate deterministic credit score from PAN via SHA256 hashing.
    Same PAN always produces same score (mimics real CIBIL behavior for demo).

    Args:
        pan: Valid PAN number (format: ABCDE1234F)

    Returns:
        Credit score in range 300-900 (realistic CIBIL range)

    Raises:
        ValueError: If PAN format is invalid
    """
    if not validate_pan(pan):
        raise ValueError(f"Invalid PAN format: {pan}. Expected format: ABCDE1234F")

    # Generate deterministic score from PAN hash
    hash_val = int(hashlib.sha256(pan.encode()).hexdigest(), 16)

    # Map to 300-900 range (realistic CIBIL range)
    # Scores below 300 don't exist in CIBIL system
    raw_score = 300 + (hash_val % 601)

    return raw_score


def get_credit_score(pan: str) -> int:
    """
    Get credit score for PAN number.
    Check demo PANs first, then simulate deterministically.

    Args:
        pan: PAN number to score

    Returns:
        Credit score 300-900
    """
    pan = pan.strip().upper()

    # Check demo PANs first for predictable demo behavior
    if pan in DEMO_PAN_SCORES:
        return DEMO_PAN_SCORES[pan]

    # Otherwise simulate deterministically
    return simulate_credit_score(pan)


def get_credit_band(score: int) -> dict:
    """
    Get credit score band details for a given score.

    Args:
        score: Credit score (300-900)

    Returns:
        Band dict with label, color, eligibility, rates, negotiation info
    """
    for band_name, band in CREDIT_SCORE_BANDS.items():
        if band["min"] <= score <= band["max"]:
            return {**band, "band_name": band_name}

    # Default to medium risk pricing if score is unexpectedly out of range.
    return {
        **CREDIT_SCORE_BANDS["MEDIUM_RISK_INTERMEDIATE"],
        "band_name": "MEDIUM_RISK_INTERMEDIATE",
    }


def mask_pan(pan: str) -> str:
    """
    Mask PAN for display: show first 5 + last 1 character.
    ABCDE1234F → ABCDE****F
    """
    pan = pan.strip().upper()
    if len(pan) < 6:
        return pan
    return f"{pan[:5]}****{pan[-1]}"
