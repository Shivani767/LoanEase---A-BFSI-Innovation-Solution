import hashlib
import logging
import random
from typing import Dict, Optional
from core.config import settings

logger = logging.getLogger("loanease.credit_score")

# Hardcoded demo PAN scores for deterministic demo flows
DEMO_PAN_SCORES = {
    "DEMO00000D": 820,   # smooth approval
    "DEMO11111E": 650,   # conditional + negotiate
    "DEMO22222F": 285,   # rejection demo
}

def simulate_cibil_score(pan_number: str) -> int:
    """Simulate CIBIL score based on PAN hash"""
    if not pan_number:
        return random.randint(settings.CREDIT_SCORE_MIN, settings.CREDIT_SCORE_MAX)
    
    # Demo mode: return deterministic hardcoded scores
    if settings.DEMO_MODE:
        demo_score = DEMO_PAN_SCORES.get(pan_number.upper())
        if demo_score is not None:
            logger.info("🎯 DEMO_MODE: Returning hardcoded CIBIL score %d for PAN %s", demo_score, pan_number)
            return demo_score
    
    # Create hash from PAN
    pan_hash = hashlib.md5(pan_number.encode()).hexdigest()
    
    # Extract numeric value from hash
    hash_num = int(pan_hash[:8], 16)
    
    # Map to CIBIL score range
    score_range = settings.CREDIT_SCORE_MAX - settings.CREDIT_SCORE_MIN
    score = settings.CREDIT_SCORE_MIN + (hash_num % (score_range + 1))
    
    return score

def calculate_credit_score(cibil_score: int, xgboost_score: float) -> Dict:
    """Calculate final credit score using weighted average"""
    # Apply weights
    weighted_cibil = cibil_score * settings.CIBIL_WEIGHT
    weighted_xgboost = xgboost_score * settings.XGBOOST_WEIGHT
    
    # Final score (normalized to 300-900 range)
    final_score = int(weighted_cibil + weighted_xgboost)
    
    # Ensure within bounds
    final_score = max(settings.CREDIT_SCORE_MIN, min(settings.CREDIT_SCORE_MAX, final_score))
    
    # Determine risk category
    if final_score >= 750:
        risk_category = "LOW"
        risk_score = 20
    elif final_score >= 700:
        risk_category = "MEDIUM"
        risk_score = 40
    elif final_score >= 650:
        risk_category = "MEDIUM-HIGH"
        risk_score = 60
    else:
        risk_category = "HIGH"
        risk_score = 80
    
    return {
        "final_score": final_score,
        "cibil_score": cibil_score,
        "xgboost_score": xgboost_score,
        "risk_category": risk_category,
        "risk_score": risk_score,
        "hard_reject": final_score < settings.HARD_REJECT_THRESHOLD
    }
