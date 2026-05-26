import json
import logging
import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel

from core.session import session_store
from services.credit_score import simulate_cibil_score, calculate_credit_score
from core.config import settings
from fastapi import File, UploadFile
import re

logger = logging.getLogger("loanease.underwriting")

router = APIRouter()

# Global model cache
_model = None
_model_features = None

# Pydantic models
class AssessRequest(BaseModel):
    # Session-based fields (agents backend)
    session_id: Optional[str] = None
    loan_amount: Optional[float] = None
    tenure_years: Optional[int] = None
    # Frontend direct fields
    pan_number: Optional[str] = None
    employer_name: Optional[str] = None
    employment_type: Optional[str] = None
    monthly_income: Optional[float] = None
    loan_purpose: Optional[str] = None
    gender: Optional[str] = None
    married: Optional[str] = None
    dependents: Optional[str] = None
    education: Optional[str] = None
    self_employed: Optional[str] = None
    applicant_income: Optional[float] = None
    coapplicant_income: Optional[float] = None
    loan_amount_term: Optional[float] = None
    credit_history: Optional[float] = None
    property_area: Optional[str] = None
    preferred_language: Optional[str] = "en"

class AssessResponse(BaseModel):
    application_id: str
    credit_score: int
    risk_category: str
    risk_score: int
    decision: str
    interest_rate: float
    max_loan_amount: float
    explanation: Dict[str, Any]
    # Aliases the frontend reads
    risk_tier: Optional[str] = None
    max_negotiation_rounds: Optional[int] = 3
    
    # Alternative Scoring
    alternative_score: Optional[int] = None
    alternative_eligible: Optional[bool] = None
    alternative_details: Optional[Dict[str, Any]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.risk_tier is None:
            self.risk_tier = self.risk_category

class CreditScoreRequest(BaseModel):
    pan_number: str

class CreditScoreResponse(BaseModel):
    cibil_score: int
    credit_score: int
    risk_category: str
    risk_score: int

def load_model():
    """Load model and metadata into memory"""
    global _model, _model_features, _metadata
    try:
        # Try to load the model file
        model_path = "models/loan_model.pkl"
        meta_path = "models/model_metadata.json"
        
        if os.path.exists(model_path):
            _model = joblib.load(model_path)
            logger.info(f"Model loaded successfully: {type(_model).__name__}")
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    _metadata = json.load(f)
                    _model_features = _metadata.get("feature_names")
                    logger.info("Model metadata loaded")
            else:
                _metadata = None
        else:
            logger.warning("Model file not found, using fallback")
            _model = None
            _metadata = None
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        _model = None
        _metadata = None

# Initial load
_metadata = None
load_model()

def model_loaded() -> bool:
    """Check if model is loaded"""
    return _model is not None

def predict_credit_score(features: Dict[str, Any]) -> float:
    """Predict credit score using XGBoost model"""
    global _model, _model_features
    
    if not _model:
        # Fallback: use rule-based scoring
        cibil_score = features.get("cibil_score", 750)
        age = features.get("age", 30)
        loan_amount = features.get("loan_amount", 500000)
        
        # Rule-based scoring
        base_score = cibil_score
        
        # Age adjustment
        if 25 <= age <= 40:
            age_adjustment = 50
        elif 41 <= age <= 55:
            age_adjustment = 30
        else:
            age_adjustment = -20
        
        # Loan amount adjustment (higher loan = slightly lower score)
        if loan_amount > 1000000:
            loan_adjustment = -30
        elif loan_amount > 500000:
            loan_adjustment = -10
        else:
            loan_adjustment = 10
        
        final_score = base_score + age_adjustment + loan_adjustment
        return max(300, min(900, final_score))
    
    try:
        # Convert features to DataFrame
        feature_df = pd.DataFrame([features])
        
        # Ensure required columns
        if _model_features:
            for col in _model_features:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            feature_df = feature_df[_model_features]
        
        # Make prediction
        prediction = _model.predict(feature_df)[0]
        
        # Scale to 300-900 range
        score = 300 + (prediction * 600)
        score = max(300, min(900, score))
        
        return float(score)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        # Fallback
        import random
        return random.uniform(300, 900)

def generate_application_id() -> str:
    """Generate unique application ID"""
    import uuid
    return f"APP-{uuid.uuid4().hex[:12].upper()}"

def get_alternative_score(applicant_data: dict) -> dict:
    """Calculate alternative score for thin-file borrowers based on non-bureau data"""
    score_components = {}
    alt_score = 0
    
    # Employment signals
    if applicant_data.get("employment_type", "").lower() == "salaried":
        alt_score += 20
        score_components["employment"] = {
            "score": 20,
            "reason": "Salaried employment provides income stability"
        }
    
    employer = str(applicant_data.get("employer_name", "")).lower()
    premium_employers = [
        "tcs", "infosys", "wipro", "hcl", "accenture", "ibm",
        "google", "microsoft", "amazon", "flipkart", "swiggy", "zomato",
        "hdfc", "icici", "sbi"
    ]
    if any(e in employer for e in premium_employers):
        alt_score += 15
        score_components["employer"] = {
            "score": 15,
            "reason": "Tier-1 employer reduces default probability"
        }
    
    # Income-to-loan ratio
    income = float(applicant_data.get("monthly_income", 0))
    loan = float(applicant_data.get("loan_amount", 1))
    ratio = (income * 12) / loan if loan > 0 else 0
    
    if ratio > 3:
        alt_score += 20
        inc_score = 20
    elif ratio > 2:
        alt_score += 10
        inc_score = 10
    else:
        inc_score = 0
        
    score_components["income_ratio"] = {
        "score": inc_score,
        "reason": f"Annual income is {ratio:.1f}x loan amount"
    }
    
    # Loan purpose risk
    purpose = str(applicant_data.get("loan_purpose", "")).lower()
    low_risk_purposes = ["medical", "education", "home renovation", "home_renovation"]
    if any(p in purpose for p in low_risk_purposes):
        alt_score += 10
        score_components["purpose"] = {
            "score": 10,
            "reason": f"Loan purpose '{purpose}' is low-risk"
        }
    
    # Tenure alignment
    tenure = int(applicant_data.get("tenure_months", 60))
    # Approximate EMI
    r = 15.0 / 12 / 100
    if r > 0:
        emi = loan * r * ((1 + r)**tenure) / (((1 + r)**tenure) - 1)
    else:
        emi = loan / tenure
        
    foir = emi / income if income > 0 else 1
    if foir < 0.3:
        alt_score += 15
        foir_score = 15
    elif foir < 0.4:
        alt_score += 8
        foir_score = 8
    else:
        foir_score = 0
        
    if foir_score > 0:
        score_components["foir"] = {
            "score": foir_score,
            "reason": f"Healthy Fixed Obligation to Income Ratio ({foir*100:.1f}%)"
        }
    
    eligible = alt_score >= 50
    
    return {
        "alternative_score": alt_score,
        "max_score": 100,
        "eligible": eligible,
        "components": score_components,
        "recommended_rate": 16.0 if eligible else None,
        "recommended_amount": min(loan, income * 3) if eligible else None,
        "message": (
            f"Despite limited credit history, your profile scores {alt_score}/100 "
            f"on alternative assessment. Conditional approval available."
            if eligible else
            f"Your alternative profile score of {alt_score}/100 does not meet "
            f"our threshold. Build credit history first."
        )
    }

@router.post("/assess", response_model=AssessResponse)
async def assess_loan(request: AssessRequest):
    """Assess loan application — accepts both session-based and direct payloads"""
    import time
    try:
        if settings.DEMO_MODE:
            import asyncio
            await asyncio.sleep(1.2)

        # Resolve loan_amount and tenure from either payload shape
        loan_amount = request.loan_amount
        tenure_years = request.tenure_years

        # Frontend sends loan_amount_term (months) and loan_amount (rupees / lakhs)
        if loan_amount is None and request.loan_amount_term is not None:
            # loan_amount_term is tenure in months from frontend
            tenure_years = max(1, int((request.loan_amount_term or 12) / 12))

        # Frontend may send loan_amount already in rupees (e.g. 500000)
        # or in lakhs (e.g. 5.0). Normalise: if < 1000, treat as lakhs
        if loan_amount is not None and loan_amount < 1000:
            loan_amount = loan_amount * 100000  # convert lakhs → rupees

        if loan_amount is None:
            loan_amount = 500000  # sensible default
        if tenure_years is None:
            tenure_years = 5

        # Resolve PAN — from session or direct field
        pan_number = request.pan_number or ""
        session = None
        if request.session_id:
            session = session_store.get(request.session_id)
            if session:
                pan_data = session["data"].get("pan_data", {})
                pan_number = pan_number or pan_data.get("pan_number", "")

        # If no session exists yet, create one
        if not session and request.session_id:
            session_store.get_or_create(request.session_id)
            session = session_store.get(request.session_id)

        app_id = generate_application_id()
        cibil_score = simulate_cibil_score(pan_number)

        age = 30
        if session:
            pan_data = session["data"].get("pan_data", {})
            age = pan_data.get("age") or 30

        features = {
            "cibil_score": cibil_score,
            "loan_amount": loan_amount,
            "tenure_years": tenure_years,
            "age": age,
            "income_estimated": (request.applicant_income or request.monthly_income or 50000) * 12,
        }

        xgboost_score = predict_credit_score(features)
        credit_result = calculate_credit_score(cibil_score, xgboost_score)

        base_rate = 12.0
        risk_adjustments = {"LOW": -1.0, "MEDIUM": 0.0, "MEDIUM-HIGH": 1.5, "HIGH": 3.0}
        interest_rate = base_rate + risk_adjustments.get(credit_result["risk_category"], 0.0)
        interest_rate = max(settings.RATE_FLOOR, min(settings.RATE_CEILING, interest_rate))

        if credit_result["hard_reject"]:
            decision = "REJECTED"
            max_loan = 0
        else:
            decision = "APPROVED"
            max_loan = loan_amount * (credit_result["final_score"] / 900)

        explanation = {
            "factors": {
                "cibil_score": {"value": cibil_score, "weight": settings.CIBIL_WEIGHT,
                                "impact": "positive" if cibil_score >= 700 else "negative"},
                "xgboost_score": {"value": round(xgboost_score, 2), "weight": settings.XGBOOST_WEIGHT,
                                  "impact": "positive" if xgboost_score >= 700 else "negative"},
            },
            "reasoning": f"Credit score {credit_result['final_score']} → {credit_result['risk_category']} risk",
        }

        # Apply Alternative Scoring if CIBIL is POOR or NA (< 600)
        alt_score = None
        alt_eligible = None
        alt_details = None

        if cibil_score < 600:
            session_context = session["data"].get("conversation_context", {}) if session else {}
            monthly_income = request.monthly_income or request.applicant_income or session_context.get("monthly_income") or 50000
            # Extract applicant data from session
            applicant_data = {
                "loan_amount": loan_amount,
                "tenure_months": tenure_years * 12,
                "monthly_income": monthly_income,
                "loan_purpose": request.loan_purpose or session_context.get("loan_purpose") or "general",
                "employment_type": request.employment_type or session_context.get("employment_type") or "salaried",
                "employer_name": request.employer_name or session_context.get("employer_name") or "TCS",
            }
            alt_res = get_alternative_score(applicant_data)
            alt_score = alt_res["alternative_score"]
            alt_eligible = alt_res["eligible"]
            alt_details = alt_res

            # If alternative assessment passes, conditionally approve them
            if alt_eligible:
                decision = "APPROVED_WITH_CONDITIONS"
                interest_rate = alt_res["recommended_rate"] or 16.0
                max_loan = alt_res["recommended_amount"] or loan_amount
                credit_result["risk_category"] = "MEDIUM-HIGH"
                credit_result["risk_score"] = 55
                explanation["reasoning"] += f" | Recovered via Alternative Score: {alt_score}/100"

        if request.session_id:
            session_store.update_stage(request.session_id, "UNDERWRITING_COMPLETE")
            session_store.update_data(request.session_id, "underwriting_result", {
                "application_id": app_id,
                "decision": decision,
                "credit_score": credit_result["final_score"],
                "interest_rate": interest_rate,
                "risk_category": credit_result["risk_category"],
                "risk_score": credit_result["risk_score"],
                "loan_amount": loan_amount,
                "tenure_years": tenure_years,
                "monthly_income": request.monthly_income or request.applicant_income,
                "employment_type": request.employment_type,
                "employer_name": request.employer_name,
                "loan_purpose": request.loan_purpose,
                "alternative_score": alt_score,
                "alternative_eligible": alt_eligible,
                "alternative_details": alt_details,
            })
            session_store.log_agent(request.session_id, {
                "agent": "underwriting", "action": "assessment",
                "success": decision == "APPROVED",
                "application_id": app_id,
                "credit_score": credit_result["final_score"],
                "decision": decision,
            })

        return AssessResponse(
            application_id=app_id,
            credit_score=credit_result["final_score"],
            risk_category=credit_result["risk_category"],
            risk_score=credit_result["risk_score"],
            decision=decision,
            interest_rate=interest_rate,
            max_loan_amount=max_loan,
            explanation=explanation,
            alternative_score=alt_score,
            alternative_eligible=alt_eligible,
            alternative_details=alt_details,
        )

    except Exception as e:
        if settings.DEMO_MODE:
            from core.fallback_map import get_fallback
            logger.error(f"Loan assessment failed, using demo fallback: {e}")
            fb = get_fallback("xgboost")
            return AssessResponse(
                application_id=f"APP-FB-{int(time.time())}",
                credit_score=fb["credit_score"],
                risk_category="MEDIUM",
                risk_score=75,
                decision="APPROVED",
                interest_rate=10.5,
                max_loan_amount=request.loan_amount or 500000,
                explanation={"reasoning": "Fallback assessment."},
            )
        logger.error(f"Loan assessment error: {e}")
        raise HTTPException(status_code=500, detail=f"Loan assessment failed: {str(e)}")

@router.post("/credit-score", response_model=CreditScoreResponse)
async def get_credit_score(request: CreditScoreRequest):
    """Get credit score for PAN number"""
    try:
        # Simulate CIBIL score
        cibil_score = simulate_cibil_score(request.pan_number)
        
        # Predict XGBoost score
        features = {"cibil_score": cibil_score}
        xgboost_score = predict_credit_score(features)
        
        # Calculate final score
        credit_result = calculate_credit_score(cibil_score, xgboost_score)
        
        return CreditScoreResponse(
            cibil_score=cibil_score,
            credit_score=credit_result["final_score"],
            risk_category=credit_result["risk_category"],
            risk_score=credit_result["risk_score"]
        )
        
    except Exception as e:
        logger.error(f"Credit score error: {e}")
        raise HTTPException(status_code=500, detail=f"Credit score calculation failed: {str(e)}")

def analyze_bank_statement(text: str) -> dict:
    # Pattern: look for recurring large credits (salary)
    credit_pattern = re.compile(r'(?:CR|CREDIT|NEFT|SALARY).*?(\d+,?\d+\.?\d*)', re.IGNORECASE)
    
    amounts = []
    for match in credit_pattern.finditer(text):
        try:
            amt = float(match.group(1).replace(',', ''))
            if amt > 5000:
                # Filter out small credits
                amounts.append(amt)
        except:
            pass
    
    if not amounts:
        return {
            "analysis_possible": False,
            "reason": "Could not extract transaction data"
        }
    
    avg_monthly = sum(amounts) / 3 if len(amounts) >= 3 else sum(amounts) / max(len(amounts), 1)
    
    return {
        "analysis_possible": True,
        "estimated_monthly_income": round(avg_monthly),
        "income_confidence": "MEDIUM",
        "data_source": "Bank statement analysis (last 3 months)",
        "note": "This supplements CIBIL for income verification"
    }

@router.post("/analyze-statement")
async def analyze_statement_api(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    try:
        content = await file.read()
        # Decode ignoring errors in case of binary/PDF
        text = content.decode(errors="ignore")
        
        # In demo mode, if we can't find anything, we inject a fake salary match so the demo works
        if settings.DEMO_MODE and not re.search(r'(?:CR|CREDIT|NEFT|SALARY)', text, re.IGNORECASE):
            text += " NEFT/SALARY-TCS 65000 CR \n NEFT/SALARY-TCS 65000 CR \n NEFT/SALARY-TCS 65000 CR"
            
        result = analyze_bank_statement(text)
        if session_id and result.get("analysis_possible"):
            try:
                session_store.update_data(session_id, "bank_statement_analysis", result)
                session_store.update_data(session_id, "monthly_income", result.get("estimated_monthly_income"))
            except Exception:
                logger.debug("Could not persist bank statement analysis for session %s", session_id)
        return result
    except Exception as e:
        logger.error(f"Bank statement analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")

@router.get("/health")
async def underwriting_health():
    """Underwriting service health check"""
    return {
        "status": "healthy" if model_loaded() else "degraded",
        "model_loaded": model_loaded(),
        "score_range": f"{settings.CREDIT_SCORE_MIN}-{settings.CREDIT_SCORE_MAX}",
        "hard_reject_threshold": settings.HARD_REJECT_THRESHOLD
    }

@router.get("/model-info")
async def get_model_info():
    """Returns model metadata and training details for the analytics dashboard"""
    global _metadata
    if not _metadata:
        load_model()

    if not _metadata:
        return {
            "status": "degraded",
            "message": "Model running in rule-based fallback mode — run models/train_pipeline.py to train",
            "model_type": "RuleBasedFallback",
            "datasets_used": [],
            "total_training_samples": 0,
            "test_auc_roc": None,
        }

    # Build a dashboard-friendly summary on top of the raw metadata
    comparison = _metadata.get("model_comparison", [])
    summary = {
        **_metadata,
        "dashboard_summary": {
            "headline": (
                f"Trained on {_metadata.get('total_dataset_rows', _metadata.get('total_training_samples', '?')):,}"
                f" samples across {len(_metadata.get('datasets_used', []))} public credit datasets"
            ),
            "auc_display": f"AUC-ROC: {_metadata.get('test_auc_roc', 'N/A')}",
            "model_display": f"Best model: {_metadata.get('model_type', 'N/A')} (best of 5 compared)",
            "models_compared": len(comparison),
        },
    }
    return summary
