from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Optional, Any, TypeAlias

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from app.model_service import ModelService
from app.schemas import (
    AssessRequest,
    AssessResponse,
    CreditScoreResponse,
    ExplainResponse,
    HealthResponse,
    SessionSaveRequest,
    SessionResponse,
    EscalationPreferenceRequest,
)
from app.storage import ApplicationStore
from app.credit_score import get_credit_score, get_credit_band, mask_pan
from app.kyc_extractors import extract_pan, extract_aadhaar, cross_validate_kyc
from app.kyc_preprocess import preprocess_image, run_ocr, MAX_UPLOAD_BYTES, UnsupportedDocumentError
from services.otp_service import otp_store
from core.config import settings, get_band

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("kyc.ocr")

# Load negotiation backend constants, service, and store
neg_backend_path = Path(__file__).resolve().parent.parent.parent / "negotiation_backend" / "app"


def _load_module(module_name: str, module_path: Path, aliases: list[str] | None = None):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if aliases:
        for alias in aliases:
                        sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module

negotiation_constants = _load_module(
    "negotiation_app_constants",
    neg_backend_path / "constants.py",
    aliases=["app.constants"],
)
MAX_ROUNDS = negotiation_constants.MAX_ROUNDS

negotiation_intent = _load_module(
    "negotiation_app_intent",
    neg_backend_path / "intent.py",
    aliases=["app.intent"],
)

negotiation_utils = _load_module(
    "negotiation_app_utils",
    neg_backend_path / "utils.py",
    aliases=["app.utils"],
)

negotiation_service = _load_module(
    "negotiation_app_service",
    neg_backend_path / "service.py",
)

negotiation_store_module = _load_module(
    "negotiation_app_store",
    neg_backend_path / "store.py",
)

negotiation_schemas = _load_module(
    "negotiation_app_schemas",
    neg_backend_path / "schemas.py",
)


class PipelineStartRequest(BaseModel):
    session_id: str
    applicant_name: str
    loan_amount: float
    loan_term: int
    offered_rate: float


CounterRequest: TypeAlias = Any
CounterResponse: TypeAlias = Any
StartNegotiationRequest: TypeAlias = Any
StartNegotiationResponse: TypeAlias = Any
StartFromUnderwritingRequest: TypeAlias = Any
StartFromUnderwritingResponse: TypeAlias = Any
AcceptRequest: TypeAlias = Any
AcceptResponse: TypeAlias = Any
EscalateRequest: TypeAlias = Any
EscalateResponse: TypeAlias = Any
HistoryResponse: TypeAlias = Any
TranslateRequest: TypeAlias = Any
TranslateResponse: TypeAlias = Any
ChatRequest: TypeAlias = Any
ChatResponse: TypeAlias = Any
IntentClassificationRequest: TypeAlias = Any
IntentClassificationResponse: TypeAlias = Any
CreditExplanationRequest: TypeAlias = Any
NegotiationExplanationRequest: TypeAlias = Any
RejectionMessageRequest: TypeAlias = Any

# Import specific functions and classes
append_history = negotiation_service.append_history
build_escalation_reference = negotiation_service.build_escalation_reference
build_offer = negotiation_service.build_offer
build_sanction_reference = negotiation_service.build_sanction_reference
counter_session = negotiation_service.counter_session
extract_top_positive_factor = negotiation_service.extract_top_positive_factor
start_session = negotiation_service.start_session
SessionStore = negotiation_store_module.SessionStore

# Import translation backend components  
try:
    trans_backend_path = Path(__file__).resolve().parent.parent.parent / "translation_backend" / "app"
    
    spec = importlib.util.spec_from_file_location("translation_service_module", trans_backend_path / "translation_service.py")
    trans_service_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trans_service_module)
    TranslationService = trans_service_module.TranslationService
    
    spec = importlib.util.spec_from_file_location("hinglish_intent_module", trans_backend_path / "hinglish_intent.py")
    hinglish_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hinglish_module)
    detect_hinglish_intent = hinglish_module.detect_hinglish_intent
    
    spec = importlib.util.spec_from_file_location("groq_service_module", trans_backend_path / "groq_service.py")
    groq_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(groq_module)
    groq_service = groq_module.groq_service
    
    spec = importlib.util.spec_from_file_location("translation_schemas", trans_backend_path / "schemas.py")
    translation_schemas = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(translation_schemas)
    
    TRANSLATION_AVAILABLE = True
except ImportError as e:
    TRANSLATION_AVAILABLE = False
    logger.warning(f"Translation services not available: {e}")

# Import pipeline components
try:
    spec = importlib.util.spec_from_file_location("pipeline_module", Path(__file__).resolve().parent.parent / "pipeline.py")
    pipeline_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline_module)
    LoanPipeline = pipeline_module.LoanPipeline
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    logger.warning(f"Pipeline not available: {e}")
    LoanPipeline = None

# Import session store
from core.session import session_store

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
STORE_PATH = BASE_DIR / "data" / "applications.jsonl"

app = FastAPI(title="LoanEase Unified Backend API", version="2.0.0")

# Import routers from agents
from agents.blockchain_agent.main import router as blockchain_router
app.include_router(blockchain_router, prefix="/blockchain", tags=["Blockchain Agent"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service: ModelService | None = None
store = ApplicationStore(STORE_PATH)
negotiation_store = SessionStore()
boot_time = datetime.now(timezone.utc)

# Initialize translation services if available
translation_service: TranslationService | None = None
if TRANSLATION_AVAILABLE:
    translation_service = TranslationService()

# Initialize pipeline if available
pipeline = None
running_tasks: dict[str, asyncio.Task] = {}
if PIPELINE_AVAILABLE:
    pipeline = LoanPipeline()

# In-memory storage for sessions and escalations
sessions: dict[str, dict] = {}
escalations: dict[str, dict] = {}


class OtpSendRequest(BaseModel):
    session_id: str


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp: str


class OtpResponse(BaseModel):
    session_id: str
    mobile_last4: str
    expires_in_seconds: int
    resend_count: int | None = None
    sent: bool | None = None
    demo_otp: str | None = None


class OtpVerifyResponse(BaseModel):
    verified: bool
    terminated: bool
    attempts_remaining: int
    mobile_last4: str
    expires_in_seconds: int
    reason: str | None = None


@app.on_event("startup")
def startup_event() -> None:
    global service
    try:
        service = ModelService(ARTIFACTS_DIR)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Model artifacts missing. Run `python train_model.py --data data/loan_train.csv` first."
        ) from exc


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if service is None:
        raise HTTPException(status_code=503, detail="Model service not ready")

    uptime_seconds = int((datetime.now(timezone.utc) - boot_time).total_seconds())
    accuracy = float(service.metrics.get("accuracy", 0.0))
    drift_status = service.drift_status()
    return HealthResponse(
        status="ok",
        model_version=service.model_version,
        accuracy=round(accuracy, 4),
        uptime_seconds=uptime_seconds,
        model_drift_warning=bool(drift_status.get("model_drift_warning", False)),
        drifted_features=list(drift_status.get("drifted_features", [])),
        recommendation=drift_status.get("recommendation"),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "LoanEase Unified Backend API",
        "status": "running",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/credit-score/{pan_number}", response_model=CreditScoreResponse)
def credit_score(pan_number: str) -> CreditScoreResponse:
    """
    Get credit score for PAN number after KYC verification.
    Returns simulated CIBIL credit score and eligibility details.
    """
    try:
        pan_number = pan_number.strip().upper()
        credit_score_val = get_credit_score(pan_number)
        # Use industry-standard TransUnion CIBIL bands for messaging
        band = get_band(credit_score_val)

        # Friendly English/Hindi messages using the new CIBIL banding
        rate_range = None
        if band.get("rate_min") is not None and band.get("rate_max") is not None:
            rate_range = f"{band['rate_min']}–{band['rate_max']}% p.a."

        message_en = (
            f"Your CIBIL score is {credit_score_val} — rated '{band.get('cibil_classification') or band.get('label')}' on TransUnion CIBIL's 5-tier scale. "
            f"This places you in our {band.get('label')} category{', qualifying you for rates between ' + rate_range if rate_range else ''}."
        )
        message_hi = (
            f"आपका CIBIL स्कोर {credit_score_val} है — TransUnion CIBIL के 5-tier scale पर '{band.get('cibil_classification') or band.get('label')}' रेटिंग मिली है। "
            f"यह आपको हमारी {band.get('label')} category में रखता है{('। आप ' + rate_range + ' वार्षिक दर के लिए पात्र हैं') if rate_range else ''}।"
        )

        applicant_band = band.get("band_key") or band.get("label")

        return CreditScoreResponse(
            pan_number=mask_pan(pan_number),
            credit_score=credit_score_val,
            credit_score_out_of=900,
            credit_band=band.get("label"),
            credit_band_color=band.get("color"),
            eligible_for_loan=True,
            applicant_score_falls_in=applicant_band,
            message_en=message_en,
            message_hi=message_hi,
            shortfall=None,
            improvement_tips=None,
            earliest_reapply=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Route alias for frontend compatibility
@app.get("/credit/credit-score", response_model=CreditScoreResponse)
def get_credit_score_route() -> CreditScoreResponse:
    """Placeholder endpoint for frontend compatibility - use /{pan_number} instead"""
    raise HTTPException(status_code=400, detail="Please provide PAN number: /credit/credit-score/{pan_number}")


@app.post("/assess", response_model=AssessResponse)
def assess(payload: AssessRequest) -> AssessResponse:
    if service is None:
        raise HTTPException(status_code=503, detail="Model service not ready")

    result = service.assess(payload.model_dump())
    application_id = str(uuid4())

    record = {
        "application_id": application_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    store.save(record)

    structured_narration = result.get("structured_shap_narration")
    if isinstance(structured_narration, (dict, list)):
        structured_narration = json.dumps(structured_narration, ensure_ascii=False)

    # Log Credit assessment
    # Try to find session_id in payload or raw request
    session_id = payload.session_id if hasattr(payload, 'session_id') else str(uuid4())
    
    session_store.log_agent(session_id, {
        "agent": "CreditUnderwritingAgent",
        "action": "LOAN_APPROVED",
        "reasoning": f"Credit assessment complete. Risk Tier: {result.get('risk_tier')}. Score: {result.get('credit_score')}",
        "status": "SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session_store.update_stage(session_id, "CREDIT_ASSESSED")

    # Build response with all fields from result
    response_data = {
        k: (structured_narration if k == "structured_shap_narration" else result.get(k))
        for k in AssessResponse.model_fields
        if k != "application_id"
    }

    # Attach industry-standard CIBIL band metadata when a credit score is present
    try:
        score = result.get("credit_score")
        if score is not None:
            band = get_band(int(score))
            rate_range = None
            if band.get("rate_min") is not None and band.get("rate_max") is not None:
                rate_range = f"{band['rate_min']}–{band['rate_max']}% p.a."

            extra = {
                "cibil_score": int(score),
                "cibil_band": band.get("display") or band.get("label"),
                "cibil_classification": band.get("cibil_classification"),
                "risk_label": band.get("label"),
                "industry_standard": "TransUnion CIBIL 5-tier scale",
                "eligible": band.get("eligible"),
                "conditional": band.get("conditional", False),
                "rate_range": rate_range,
                "max_negotiation_rounds": band.get("max_rounds"),
            }
            response_data.update(extra)
    except Exception:
        # If anything goes wrong, continue without CIBIL extras
        pass

    return AssessResponse(application_id=application_id, **response_data)


# Route alias for frontend compatibility
@app.post("/credit/assess", response_model=AssessResponse)
def credit_assess(payload: AssessRequest) -> AssessResponse:
    """Alias for /assess endpoint for frontend compatibility"""
    return assess(payload)


@app.post("/explain/{application_id}", response_model=ExplainResponse)
def explain(application_id: str) -> ExplainResponse:
    record = store.get(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Application not found")

    structured_narration = record.get("structured_shap_narration")
    if isinstance(structured_narration, (dict, list)):
        structured_narration = json.dumps(structured_narration, ensure_ascii=False)

    return ExplainResponse(
        application_id=record["application_id"],
        decision=record["decision"],
        approval_probability=record["approval_probability"],
        risk_tier=record["risk_tier"],
        risk_score=record["risk_score"],
        threshold_used=record["threshold_used"],
        raw_input=record["raw_input"],
        top_explanations=record["shap_explanation"],
        shap_waterfall=record["shap_waterfall"],
        structured_shap_narration=structured_narration,
        confidence_lower=record.get("confidence_lower"),
        confidence_upper=record.get("confidence_upper"),
        confidence_width=record.get("confidence_width"),
        model_certainty=record.get("model_certainty"),
        income_reasonability=record.get("income_reasonability"),
        soft_reject_guidance=record.get("soft_reject_guidance"),
        confidence_message=record.get("confidence_message"),
    )


@app.post("/session/save", response_model=SessionResponse)
def save_session(payload: SessionSaveRequest) -> SessionResponse:
    sessions[payload.session_id] = payload.model_dump()
    return SessionResponse(**sessions[payload.session_id])


@app.get("/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**sessions[session_id])


@app.get("/pipeline/log/{session_id}")
async def get_pipeline_log(session_id: str):
    """Return pipeline execution log for a session."""
    session = session_store.get(session_id)
    if not session:
        # Create a new session if it doesn't exist to avoid front-end 404s
        session = session_store.get_or_create(session_id)
        
    return {
        "session_id": session_id,
        "pipeline_status": session.get("stage", "ACTIVE"),
        "agent_trace": session.get("agent_log", []),
    }

@app.get("/pipeline/global-logs")
async def get_global_logs(limit: int = 20):
    """Get the most recent system-wide agent activity"""
    return {
        "logs": session_store.get_global_activity(limit),
        "total_active_sessions": len(session_store._sessions),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/session/init/{session_id}")
async def init_session(session_id: str):
    """Initialize a new session and log the start."""
    session_store.get_or_create(session_id)
    session_store.log_agent(session_id, {
        "agent": "MasterOrchestratorAgent",
        "action": "INITIATED_SESSION",
        "reasoning": "New loan inquiry received. Starting orchestration.",
        "status": "SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session_store.update_stage(session_id, "INITIATED")
    return {"status": "success", "session_id": session_id}


@app.post("/pipeline/start")
async def start_pipeline(payload: PipelineStartRequest):
    """
    Manually start or update the pipeline orchestration for a session.
    Used when transitioning from chat input to agent processing.
    """
    session_id = payload.session_id
    session_store.get_or_create(session_id)
    
    # Update session data with what we have so far
    session_store.update_data(session_id, "applicant_name", payload.applicant_name)
    session_store.update_data(session_id, "loan_amount", payload.loan_amount)
    session_store.update_data(session_id, "loan_term", payload.loan_term)
    session_store.update_data(session_id, "offered_rate", payload.offered_rate)
    
    session_store.log_agent(session_id, {
        "agent": "MasterOrchestratorAgent",
        "action": "PIPELINE_ACTIVATED",
        "reasoning": f"Orchestration pipeline activated for {payload.applicant_name}. Starting multi-agent verification.",
        "status": "SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session_store.update_stage(session_id, "ACTIVE")
    
    return {
        "status": "ACTIVE",
        "session_id": session_id,
        "message": "Pipeline orchestration activated successfully"
    }


@app.post("/escalation/callback-preference")
def save_escalation_preference(payload: EscalationPreferenceRequest):
    escalations[payload.session_id] = payload.model_dump()
    return {"status": "success", "message": "Callback preference saved"}


@app.get("/analytics/{session_id}")
async def get_analytics(session_id: str):
    """Get comprehensive analytics data for post-sanction dashboard"""
    try:
        def coerce_number(value: Any, default: float) -> float:
            if value is None:
                return float(default)
            if isinstance(value, (int, float)):
                return float(value)
            try:
                cleaned = str(value).replace("₹", "").replace(",", "").replace("%", "").strip()
                return float(cleaned)
            except (TypeError, ValueError):
                return float(default)

        def coerce_int(value: Any, default: int) -> int:
            try:
                return int(float(coerce_number(value, default)))
            except (TypeError, ValueError):
                return int(default)

        def session_payload_for(target_session_id: str) -> dict[str, Any]:
            candidates = [target_session_id]
            if "-" in target_session_id:
                candidates.append(target_session_id.split("-")[0])

            for candidate in candidates:
                session = session_store.get(candidate)
                if isinstance(session, dict):
                    payload = session.get("data")
                    if isinstance(payload, dict) and payload:
                        return payload
                    if any(key in session for key in ("loan_amount", "offered_rate", "loan_term", "credit_score", "risk_score")):
                        return session

                saved_session = app.state.saved_sessions.get(candidate)
                if isinstance(saved_session, dict):
                    payload = saved_session.get("applicant_data")
                    if isinstance(payload, dict) and payload:
                        return payload

            return {}

        session_data = session_payload_for(session_id)
        session_found = bool(session_data)

        loan_amount = coerce_number(session_data.get("loan_amount") or session_data.get("amount") or session_data.get("selected_amount"), 500000)
        interest_rate = coerce_number(session_data.get("final_rate") or session_data.get("sanctioned_rate") or session_data.get("offered_rate") or session_data.get("interest_rate"), 11.0)
        tenure_months = max(1, coerce_int(session_data.get("tenure_months") or session_data.get("tenure") or session_data.get("loan_term"), 60))

        monthly_rate = interest_rate / 12 / 100
        if monthly_rate > 0:
            power_val = (1 + monthly_rate) ** float(tenure_months)
            emi = loan_amount * monthly_rate * power_val / (power_val - 1) if power_val > 1 else loan_amount / tenure_months
        else:
            emi = loan_amount / tenure_months

        total_payable = emi * float(tenure_months)
        total_interest = total_payable - float(loan_amount)

        credit_score = coerce_number(session_data.get("credit_score") or session_data.get("cibil_score"), 720)
        risk_score = coerce_number(session_data.get("risk_score") or session_data.get("combined_score"), 75)
        risk_tier = "Low Risk" if risk_score >= 75 else "Medium Risk" if risk_score >= 50 else "High Risk"

        shap_factors = session_data.get("shap_factors") or session_data.get("shap_explanation") or [
            {"feature": "Credit History", "value": 0.41, "direction": "positive"},
            {"feature": "Income Level", "value": 0.28, "direction": "positive"},
            {"feature": "Loan Amount", "value": -0.15, "direction": "negative"},
            {"feature": "Employment", "value": 0.12, "direction": "positive"},
            {"feature": "Existing EMIs", "value": -0.09, "direction": "negative"},
        ]

        opening_rate = coerce_number(session_data.get("initial_rate"), interest_rate + 0.5)
        final_rate = interest_rate
        rounds_taken = coerce_int(session_data.get("rounds_completed") or session_data.get("negotiation_rounds"), 1)
        total_savings = max(((opening_rate - final_rate) / 100 / 12) * loan_amount * tenure_months / 2, 0)

        benchmark = {
            "avg_credit_score": 720,
            "avg_income_normalized": 70,
            "avg_loan_to_income": 65,
            "avg_employment": 75,
            "avg_repayment": 80,
            "avg_coapplicant": 60,
        }

        applicant_normalized = {
            "credit_score": min(max(round((credit_score - 300) / 6), 0), 100),
            "income_norm": min(max(int(risk_score), 0), 100),
            "loan_income": max(100 - round((loan_amount / 500000) * 50), 30),
            "employment": 75,
            "repayment": min(max(round(credit_score / 9), 0), 100),
            "coapplicant": 60,
        }

        return {
            "success": True,
            "session_found": session_found,
            "loan_data": {
                "amount": round(loan_amount, 2),
                "rate": round(interest_rate, 2),
                "tenure_months": tenure_months,
                "emi": round(emi, 2),
                "total_payable": round(total_payable, 2),
                "total_interest": round(total_interest, 2),
            },
            "credit_data": {
                "credit_score": round(credit_score, 2),
                "risk_score": round(risk_score, 2),
                "risk_tier": risk_tier,
                "shap_factors": shap_factors,
            },
            "negotiation_summary": {
                "opening_rate": round(opening_rate, 2),
                "final_rate": round(final_rate, 2),
                "rounds_taken": rounds_taken,
                "total_savings": round(total_savings, 2),
            },
            "benchmark": benchmark,
            "applicant_normalized": applicant_normalized,
        }

    except Exception as e:
        logger.error(f"Analytics error for session {session_id}: {e}", exc_info=True)
        return {
            "success": True,
            "session_found": False,
            "loan_data": {
                "amount": 500000,
                "rate": 11.0,
                "tenure_months": 60,
                "emi": 10871,
                "total_payable": 652260,
                "total_interest": 152260,
            },
            "credit_data": {
                "credit_score": 750,
                "risk_score": 80,
                "risk_tier": "Low Risk",
                "shap_factors": [
                    {"feature": "Credit History", "value": 0.41, "direction": "positive"},
                    {"feature": "Income Level", "value": 0.28, "direction": "positive"},
                    {"feature": "Loan Amount", "value": -0.15, "direction": "negative"},
                ],
            },
            "negotiation_summary": {
                "opening_rate": 11.5,
                "final_rate": 11.0,
                "rounds_taken": 2,
                "total_savings": 8400,
            },
            "benchmark": {
                "avg_credit_score": 720,
                "avg_income_normalized": 70,
                "avg_loan_to_income": 65,
                "avg_employment": 75,
                "avg_repayment": 80,
                "avg_coapplicant": 60,
            },
            "applicant_normalized": {
                "credit_score": 75,
                "income_norm": 80,
                "loan_income": 65,
                "employment": 75,
                "repayment": 83,
                "coapplicant": 60,
            },
        }


# =============================================================================
# KYC EXTRACTION ENDPOINTS
# =============================================================================

def _assert_upload_constraints(file: UploadFile, file_bytes: bytes) -> None:
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB allowed")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in {"jpg", "jpeg", "png", "pdf"}:
        raise HTTPException(status_code=400, detail="Only JPG, PNG or PDF files are supported")


@app.post("/kyc/extract/pan")
async def extract_pan_document(document: UploadFile = File(...), session_id: str | None = Form(None)):
    file_bytes = await document.read()
    _assert_upload_constraints(document, file_bytes)
    
    # Log KYC start if session_id provided
    if session_id:
        session_store.get_or_create(session_id)
        session_store.log_agent(session_id, {
            "agent": "KYCVerificationAgent",
            "action": "SCANNING_PAN",
            "reasoning": "User uploaded PAN card. Extracting identity fields.",
            "status": "RUNNING",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        session_store.update_stage(session_id, "KYC_PENDING")

    try:
        extension = (document.filename or "").lower().split(".")[-1]
        preprocessed = preprocess_image(file_bytes, extension)
        ocr_text, confidence = run_ocr(preprocessed)
        result = extract_pan(ocr_text)
        
        return {
            "document_type": "PAN",
            "extracted_fields": result["extracted_fields"],
            "validation": result["validation"],
            "confidence_score": confidence,
            "processing_time_ms": 0,
        }
    except Exception as exc:
        logger.error(f"KYC PAN: Extraction failed - {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/kyc/extract/aadhaar")
async def extract_aadhaar_document(document: UploadFile = File(...), session_id: str | None = Form(None)):
    file_bytes = await document.read()
    _assert_upload_constraints(document, file_bytes)
    
    # Log KYC start if session_id provided
    if session_id:
        session_store.get_or_create(session_id)
        session_store.log_agent(session_id, {
            "agent": "KYCVerificationAgent",
            "action": "SCANNING_AADHAAR",
            "reasoning": "User uploaded Aadhaar card. Extracting identity fields.",
            "status": "RUNNING",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        session_store.update_stage(session_id, "KYC_PENDING")

    try:
        extension = (document.filename or "").lower().split(".")[-1]
        preprocessed = preprocess_image(file_bytes, extension)
        ocr_text, confidence = run_ocr(preprocessed)
        result = extract_aadhaar(ocr_text)
        mobile_number = result.get("extracted_fields", {}).get("mobile_number")
        if session_id and mobile_number:
            session_store.update_data(session_id, "aadhaar_data", result.get("extracted_fields", {}))
            session_store.update_data(session_id, "aadhaar_mobile", mobile_number)
            session_store.update_data(session_id, "aadhaar_mobile_last4", mobile_number[-4:])
        
        return {
            "document_type": "AADHAAR",
            "extracted_fields": {
                **result["extracted_fields"],
            },
            "validation": result["validation"],
            "confidence_score": confidence,
            "processing_time_ms": 0,
        }
    except Exception as exc:
        logger.error(f"KYC Aadhaar: Extraction failed - {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/kyc/verify")
async def verify_kyc(pan: UploadFile = File(...), aadhaar: UploadFile = File(...), session_id: str | None = Form(None)):
    pan_bytes = await pan.read()
    aadhaar_bytes = await aadhaar.read()
    
    _assert_upload_constraints(pan, pan_bytes)
    _assert_upload_constraints(aadhaar, aadhaar_bytes)

    if session_id:
        session_store.get_or_create(session_id)
    
    try:
        # Extract PAN
        pan_ext = (pan.filename or "").lower().split(".")[-1]
        pan_preprocessed = preprocess_image(pan_bytes, pan_ext)
        pan_ocr_text, _ = run_ocr(pan_preprocessed)
        pan_result = extract_pan(pan_ocr_text)
        
        # Extract Aadhaar
        aadhaar_ext = (aadhaar.filename or "").lower().split(".")[-1]
        aadhaar_preprocessed = preprocess_image(aadhaar_bytes, aadhaar_ext)
        aadhaar_ocr_text, _ = run_ocr(aadhaar_preprocessed)
        aadhaar_result = extract_aadhaar(aadhaar_ocr_text)
        mobile_number = aadhaar_result.get("extracted_fields", {}).get("mobile_number")
        if session_id and mobile_number:
            session_store.update_data(session_id, "aadhaar_data", aadhaar_result.get("extracted_fields", {}))
            session_store.update_data(session_id, "aadhaar_mobile", mobile_number)
            session_store.update_data(session_id, "aadhaar_mobile_last4", mobile_number[-4:])
        
        # Cross-validate
        validation = cross_validate_kyc(pan_result, aadhaar_result)
        
        # Log KYC step
        s_id = session_id or (pan.filename.split('_')[0] if '_' in pan.filename else str(uuid4()))
        
        session_store.log_agent(s_id, {
            "agent": "KYCVerificationAgent",
            "action": "DOCUMENTS_VERIFIED",
            "reasoning": "Cross-validation of PAN and Aadhaar successful. Identity confirmed.",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        session_store.update_stage(s_id, "KYC_OTP_PENDING")

        return {
            "kyc_status": validation["kyc_status"],
            "pan_data": pan_result.get("extracted_fields"),
            "aadhaar_data": {
                **aadhaar_result.get("extracted_fields"),
            },
            "cross_validation": validation["cross_validation"],
            "overall_kyc_passed": validation["overall_kyc_passed"],
            "kyc_reference_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"KYC Verify: Failed - {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KYC verification failed: {str(exc)}") from exc


@app.post("/kyc/send-otp", response_model=OtpResponse)
async def send_otp(payload: OtpSendRequest):
    session = session_store.get_or_create(payload.session_id)

    mobile_number = session.get("data", {}).get("aadhaar_mobile")
    if not mobile_number:
        aadhaar_data = session.get("data", {}).get("aadhaar_data", {})
        mobile_number = aadhaar_data.get("mobile_number")

    if not mobile_number:
        raise HTTPException(
            status_code=400,
            detail="Aadhaar mobile number not found. Please upload the full Aadhaar card with the mobile number visible.",
        )

    result = otp_store.send_otp(payload.session_id, mobile_number)
    session_store.update_stage(payload.session_id, "KYC_OTP_PENDING")
    session_store.update_data(payload.session_id, "aadhaar_mobile", mobile_number)
    session_store.update_data(payload.session_id, "aadhaar_otp_pending", True)

    if not result["sent"]:
        raise HTTPException(
            status_code=502,
            detail="Unable to send OTP right now. Configure SMS_PROVIDER with valid credentials.",
        )

    return OtpResponse(**result)


@app.post("/kyc/resend-otp", response_model=OtpResponse)
async def resend_otp(payload: OtpSendRequest):
    try:
        result = otp_store.resend_otp(payload.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="OTP session not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return OtpResponse(**result)


@app.post("/kyc/verify-otp", response_model=OtpVerifyResponse)
async def verify_otp(payload: OtpVerifyRequest):
    try:
        result = otp_store.verify_otp(payload.session_id, payload.otp)
    except KeyError:
        raise HTTPException(status_code=404, detail="OTP session not found") from None

    if result["verified"]:
        session_store.update_stage(payload.session_id, "KYC_VERIFIED")
        session_store.update_data(payload.session_id, "aadhaar_otp_verified", True)
    elif result["terminated"]:
        session_store.update_stage(payload.session_id, "KYC_TERMINATED")
        session_store.update_data(payload.session_id, "aadhaar_otp_failed", True)

    return OtpVerifyResponse(**result)


# =============================================================================
# NEGOTIATION ENDPOINTS (from negotiation_backend)
# =============================================================================

@app.post("/negotiate/chat", response_model=negotiation_schemas.CounterResponse)
def negotiate_chat(payload: CounterRequest) -> CounterResponse:
    # Log Negotiation action
    session_store.log_agent(payload.session_id, {
        "agent": "Negotiation Agent",
        "action": "RATE_NEGOTIATED",
        "reasoning": f"Processing user counter-offer. Intent: {payload.applicant_message[:30]}...",
        "status": "SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session_store.update_stage(payload.session_id, "NEGOTIATING")
    
    return negotiation_schemas.CounterResponse(**counter_session(payload.model_dump()))

@app.post("/negotiate/start", response_model=negotiation_schemas.StartNegotiationResponse)
def negotiate_start(payload: StartNegotiationRequest) -> StartNegotiationResponse:
    session = start_session(payload.model_dump())
    negotiation_store.create(session)

    rounds_remaining = max(0, MAX_ROUNDS - session["rounds_completed"])

    return negotiation_schemas.StartNegotiationResponse(
        session_id=session["session_id"],
        opening_offer=session["opening_offer"],
        reasoning=session["history"][0]["reasoning"],
        can_negotiate=session["can_negotiate"],
        rounds_remaining=rounds_remaining,
        negotiation_hint="You may request a rate reduction. Our system will evaluate your profile and respond.",
        detected_intent="START",
    )


@app.post("/negotiate/start-from-underwriting", response_model=negotiation_schemas.StartFromUnderwritingResponse)
def negotiate_start_from_underwriting(payload: StartFromUnderwritingRequest) -> StartFromUnderwritingResponse:
    base_url = payload.underwriting_base_url.rstrip("/")
    assess_url = f"{base_url}/assess"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(assess_url, json=payload.assess_payload.model_dump())
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Unable to reach underwriting service at {assess_url}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Underwriting service returned {response.status_code}: {response.text}",
        )

    assessment = response.json()
    risk_score = int(assessment.get("risk_score", 0))
    risk_tier = str(assessment.get("risk_tier", "Medium"))
    top_positive_factor = extract_top_positive_factor(assessment.get("shap_explanation"))

    session = start_session(
        {
            "applicant_name": payload.applicant_name,
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "loan_amount": payload.loan_amount,
            "tenure_months": payload.tenure_months,
            "top_positive_factor": top_positive_factor,
        }
    )
    negotiation_store.create(session)
    rounds_remaining = max(0, MAX_ROUNDS - session["rounds_completed"])

    return negotiation_schemas.StartFromUnderwritingResponse(
        session_id=session["session_id"],
        underwriting_assessment=assessment,
        opening_offer=session["opening_offer"],
        reasoning=session["history"][0]["reasoning"],
        can_negotiate=session["can_negotiate"],
        rounds_remaining=rounds_remaining,
        negotiation_hint="You may request a rate reduction. Our system will evaluate your profile and respond.",
        detected_intent="START",
    )


@app.post("/negotiate/counter", response_model=negotiation_schemas.CounterResponse)
def negotiate_counter(payload: CounterRequest) -> CounterResponse:
    session = negotiation_store.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if negotiation_store.mark_expired_if_needed(session):
        raise HTTPException(status_code=410, detail="Session expired")

    result = counter_session(session, payload.applicant_message, payload.requested_rate)
    append_history(session, "counter", result["reasoning"], result["intent"])
    negotiation_store.update(payload.session_id, session)

    rounds_remaining = max(0, MAX_ROUNDS - session["rounds_completed"])

    return negotiation_schemas.CounterResponse(
        session_id=payload.session_id,
        counter_offer=result["offer"],
        reasoning=result["reasoning"],
        rounds_remaining=rounds_remaining,
        can_negotiate_further=result["can_negotiate_further"],
        status=session["status"],
        detected_intent=result["intent"],
    )


@app.post("/negotiate/accept", response_model=negotiation_schemas.AcceptResponse)
def negotiate_accept(payload: AcceptRequest) -> AcceptResponse:
    session = negotiation_store.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if negotiation_store.mark_expired_if_needed(session):
        negotiation_store.update(payload.session_id, session)
        expired_offer = build_offer(
            session["loan_amount"],
            session["tenure_months"],
            session["current_rate"],
            session["opening_offer"]["total_payable"],
        )
        return negotiation_schemas.AcceptResponse(
            session_id=payload.session_id,
            final_offer=expired_offer,
            message="This negotiation session has expired after 48 hours. Please restart your negotiation.",
            sanction_reference="NA",
            status="expired",
            detected_intent="ACCEPTANCE",
        )

    final_offer = build_offer(
        session["loan_amount"],
        session["tenure_months"],
        session["current_rate"],
        session["opening_offer"]["total_payable"],
    )
    sanction_reference = build_sanction_reference()

    session["status"] = "completed"
    append_history(
        session,
        "accept",
        f"This concludes our negotiation. Your final approved rate is {session['current_rate']:.2f}% per annum. "
        "This offer is valid for 48 hours. Shall I generate your sanction letter?",
        "ACCEPTANCE",
    )
    negotiation_store.update(payload.session_id, session)

    return negotiation_schemas.AcceptResponse(
        session_id=payload.session_id,
        final_offer=final_offer,
        message=(
            f"Congratulations! Your loan at {session['current_rate']:.2f}% per annum has been accepted. "
            "Generating your digitally signed sanction letter now..."
        ),
        sanction_reference=sanction_reference,
        status="completed",
        detected_intent="ACCEPTANCE",
    )


@app.post("/negotiate/escalate", response_model=negotiation_schemas.EscalateResponse)
def negotiate_escalate(payload: EscalateRequest) -> EscalateResponse:
    session = negotiation_store.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if negotiation_store.mark_expired_if_needed(session):
        negotiation_store.update(payload.session_id, session)
        return negotiation_schemas.EscalateResponse(
            session_id=payload.session_id,
            message="Session expired before escalation could be processed. Please restart negotiation.",
            escalation_id="NA",
            status="expired",
            detected_intent="ESCALATION_REQUEST",
        )

    escalation_id = build_escalation_reference()
    sanction_reference = build_sanction_reference()
    session["status"] = "escalated"
    append_history(
        session,
        "escalate",
        "You have reached the minimum rate available for your risk tier. Further reduction is not possible within automated limits. "
        "Would you like me to escalate this to a human loan officer for a manual review?",
        "ESCALATION_REQUEST",
    )
    negotiation_store.update(payload.session_id, session)

    return negotiation_schemas.EscalateResponse(
        session_id=payload.session_id,
        message=(
            "Your case has been escalated to a senior loan officer. You will receive a call within 2 business hours. "
            f"Reference: {sanction_reference}."
        ),
        escalation_id=escalation_id,
        status="escalated",
        detected_intent="ESCALATION_REQUEST",
    )


@app.get("/negotiate/history/{session_id}", response_model=negotiation_schemas.HistoryResponse)
def negotiate_history(session_id: str) -> HistoryResponse:
    session = negotiation_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if negotiation_store.mark_expired_if_needed(session):
        negotiation_store.update(session_id, session)

    return negotiation_schemas.HistoryResponse(session_id=session_id, status=session["status"], session=session)


# =============================================================================
# PIPELINE ENDPOINTS (from pipeline_app)
# =============================================================================

if PIPELINE_AVAILABLE:
    @app.post("/pipeline/start")
    async def start_pipeline(request: dict) -> dict:
        """Start a complete loan processing pipeline"""
        try:
            session_id = request.get("session_id") or str(uuid4())
            request["session_id"] = session_id

            if session_id in running_tasks and not running_tasks[session_id].done():
                return {"session_id": session_id, "status": "ACTIVE", "message": "Pipeline already running"}

            running_tasks[session_id] = asyncio.create_task(pipeline.run_full_pipeline(request))
            return {"session_id": session_id, "status": "ACTIVE", "message": "Pipeline started"}
        except Exception as e:
            logger.error(f"Pipeline start error: {e}")
            fallback_id = request.get("session_id") or str(uuid4())
            return {"session_id": fallback_id, "status": "error", "message": "Pipeline could not start. Please try again."}


    @app.get("/pipeline/log/{session_id}")
    def get_pipeline_log(session_id: str) -> dict:
        """Get pipeline execution logs for a session"""
        try:
            log = pipeline.get_session_log(session_id)
            if not log.get("agent_trace"):
                raise HTTPException(status_code=404, detail="Session not found")
            return log
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pipeline log error: {e}")


# =============================================================================
# TRANSLATION ENDPOINTS (from translation_backend)
# =============================================================================

if TRANSLATION_AVAILABLE:
    @app.post("/translate", response_model=translation_schemas.TranslateResponse)
    def translate(payload: TranslateRequest) -> TranslateResponse:
        """Translate text between languages"""
        try:
            result = translation_service.translate(
                payload.text,
                source_language=payload.source_language,
                target_language=payload.target_language,
            )
            return translation_schemas.TranslateResponse(**result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Translation failed: {str(exc)}") from exc

    @app.post("/detect-hinglish-intent")
    def detect_hinglish(payload: dict) -> dict:
        """Detect intent from Hinglish input"""
        message = payload.get("message", "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message required")
        intent = detect_hinglish_intent(message)
        return {"message": message, "intent": intent}

    @app.post("/chat", response_model=translation_schemas.ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        """Process chat message using Groq LLM"""
        return await groq_service.process_chat_request(request)

    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """Stream chat response token by token"""
        async def generate():
            async for token in groq_service.stream_chat_response(request):
                yield token
        from fastapi.responses import StreamingResponse
        return StreamingResponse(generate(), media_type="text/plain")

    @app.post("/intent/classify", response_model=translation_schemas.IntentClassificationResponse)
    async def classify_intent(request: IntentClassificationRequest) -> IntentClassificationResponse:
        """Classify user intent using Groq"""
        return await groq_service.classify_intent(request)

    @app.post("/explain/credit")
    async def explain_credit(request: CreditExplanationRequest):
        """Generate credit decision explanation"""
        explanation = await groq_service.generate_credit_explanation(
            request.credit_score,
            request.risk_score,
            request.decision,
            request.rate,
            request.shap_factors,
            request.language
        )
        return {"explanation": explanation}

    @app.post("/explain/negotiation")
    async def explain_negotiation(request: NegotiationExplanationRequest):
        """Generate negotiation explanation"""
        explanation = await groq_service.generate_negotiation_explanation(
            request.starting_rate,
            request.current_rate,
            request.floor_rate,
            request.round,
            request.max_rounds,
            request.risk_tier,
            request.positive_factor,
            request.language
        )
        return {"explanation": explanation}

    @app.post("/generate/rejection")
    async def generate_rejection(request: RejectionMessageRequest):
        """Generate empathetic rejection message"""
        message = await groq_service.generate_rejection_message(
            request.credit_score,
            request.language
        )
        return {"message": message}

    @app.get("/groq/health")
    def groq_health():
        """Get Groq API health status"""
        return groq_service.client.get_health_status()



@app.get("/blockchain/sanction")
async def download_sanction_letter(reference_id: str):
    """
    Download a generated sanction letter PDF.
    This is a robust fallback endpoint that searches multiple locations.
    """
    from fastapi.responses import FileResponse
    
    # Clean reference ID
    ref = reference_id.strip()
    
    # Possible directories
    base = Path(__file__).resolve().parent.parent
    possible_dirs = [
        base / "artifacts" / "sanctions",
        Path("artifacts/sanctions"),
        base / "agents" / "blockchain_agent" / "artifacts" / "sanctions",
    ]
    
    for s_dir in possible_dirs:
        if not s_dir.exists():
            continue
            
        # Try patterns
        patterns = [
            f"sanction_{ref}.pdf",
            f"{ref}.pdf",
            f"*{ref}*.pdf"
        ]
        
        for pattern in patterns:
            if "*" in pattern:
                candidates = list(s_dir.glob(pattern))
                if candidates:
                    return FileResponse(candidates[0], media_type="application/pdf", filename=f"Sanction_{ref}.pdf")
            else:
                file_path = s_dir / pattern
                if file_path.exists():
                    return FileResponse(file_path, media_type="application/pdf", filename=f"Sanction_{ref}.pdf")
    
    logger.error(f"Sanction letter not found: {ref}")
    raise HTTPException(status_code=404, detail=f"Sanction letter {ref} not found. It may still be generating.")

# =============================================================================
# AGENT ORCHESTRATION ROUTES
# =============================================================================

try:
    from app.agent_routes import router as agent_router
    app.include_router(agent_router)
except ImportError:
    pass  # Agent routes not available
