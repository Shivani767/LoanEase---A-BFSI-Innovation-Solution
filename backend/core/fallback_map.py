"""
Centralized fallback mapping for LoanEase Demo Mode.

Provides hardcoded responses for various components when they fail, 
ensuring the demo never stops due to API limits or model errors.
"""

from typing import Any, Dict
import logging

logger = logging.getLogger("loanease.fallback")

FALLBACK_RESPONSES = {
    "groq": {
        "text": "I have carefully reviewed your profile. Based on our internal risk models, you are eligible for a competitive interest rate. Let's proceed with the documentation.",
        "trace": {"agent": "FallbackAgent", "confidence": 0.85, "engine": "HardcodedFallback"}
    },
    "xgboost": {
        "credit_score": 745,
        "risk_tier": "B1 (Prime)",
        "probability_of_default": 0.045
    },
    "blockchain": {
        "transaction_id": "TXN-FALLBACK-000000",
        "block_hash": "H6v7W2...fallback",
        "status": "VERIFIED_OFFLINE"
    }
}

def get_fallback(component: str) -> Dict[str, Any]:
    """Get the fallback response for a specific component."""
    logger.warning(f"⚠️ COMPONENT FAILURE: Using fallback response for '{component}'")
    return FALLBACK_RESPONSES.get(component, {"error": "No fallback defined"})
