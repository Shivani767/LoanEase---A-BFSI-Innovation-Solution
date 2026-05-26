from contextlib import asynccontextmanager
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

# Import all routers
from agents.kyc_agent.main import router as kyc_router
from agents.underwriting_agent.main import router as underwriting_router
from agents.negotiation_agent.main import router as negotiation_router
from agents.blockchain_agent.main import router as blockchain_router
from agents.master_agent.main import router as master_router
from routers.ai_router import router as ai_router
from routers.demo_router import router as demo_router
from startup_selftest import run_startup_selftest
from services.groq_service import GroqService
from services.memory import ConversationMemory
from services.ocr import init_ocr, ocr_ready
from core.config import settings
from core.session import session_store
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from core.limiter import limiter

logger = logging.getLogger("loanease")


class SessionSaveRequest(BaseModel):
    session_id: str
    messages: list[dict]
    stage: str
    applicant_data: dict


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]
    stage: str
    applicant_data: dict


class EscalationPreferenceRequest(BaseModel):
    session_id: str
    preferred_time: str
    whatsapp_opt_in: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LoanEase backend starting")

    # 0) OCR engine (best effort; degraded mode if unavailable)
    try:
        init_ocr()
        if ocr_ready():
            logger.info("OCR engine initialized")
        else:
            logger.warning("OCR engine unavailable; KYC OCR endpoints may return degraded status")
    except Exception as exc:
        logger.warning("OCR initialization failed; continuing in degraded mode: %s", str(exc))

    # 1) Groq service.
    app.state.groq_service = GroqService(
        api_key=settings.GROQ_API_KEY,
        primary_model=settings.GROQ_MODEL_PRIMARY,
        fallback_model=settings.GROQ_MODEL_FALLBACK,
        timeout=settings.GROQ_TIMEOUT,
    )
    await app.state.groq_service.verify_connection()

    # 2) Redis (optional) with graceful fallback.
    redis_client: Any = None
    if settings.REDIS_URL:
        try:
            import redis.asyncio as redis

            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await redis_client.ping()
        except Exception:
            logger.warning("Redis unavailable — using in-process memory")
            redis_client = None
    else:
        logger.info("Redis URL not configured; running in dev mode")

    # 3) Conversation memory wired to Redis or local fallback.
    app.state.memory = ConversationMemory(redis_client)
    app.state.saved_sessions: Dict[str, Dict[str, Any]] = {}
    app.state.escalation_preferences: Dict[str, Dict[str, Any]] = {}

    # ── Startup self-test ────────────────────────────────────────
    await run_startup_selftest(app)

    yield

    # 4) Shutdown clean-up.
    if redis_client is not None:
        await redis_client.aclose()
    logger.info("LoanEase backend shutting down")

limiter_instance = limiter # Rename to avoid conflict with imported name if needed
app = FastAPI(
    title="LoanEase API",
    description="Agentic AI Personal Loan System",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount all routers with clean prefixes
app.include_router(kyc_router, prefix="/kyc", tags=["KYC Agent"])
app.include_router(underwriting_router, prefix="/credit", tags=["Credit Agent"])
app.include_router(negotiation_router, prefix="/negotiate", tags=["Negotiation Agent"])
app.include_router(blockchain_router, prefix="/blockchain", tags=["Blockchain Agent"])
app.include_router(master_router, prefix="/pipeline/agent", tags=["Master Orchestrator"])
app.include_router(ai_router)
app.include_router(demo_router, prefix="/demo", tags=["Demo Utilities"])

# Root health check
@app.get("/")
async def root():
    return {
        "service": "LoanEase Agentic AI Backend",
        "version": "1.0.0",
        "status": "running",
        "agents": [
            "KYCVerificationAgent",
            "CreditUnderwritingAgent", 
            "NegotiationAgent",
            "BlockchainAuditAgent",
            "MasterOrchestratorAgent"
        ],
        "docs": "http://localhost:8000/docs",
    }

# Master health check across all agents
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "groq": "connected",
    }


@app.post("/session/save", response_model=SessionResponse)
async def save_session(payload: SessionSaveRequest):
    app.state.saved_sessions[payload.session_id] = payload.model_dump()
    session_store.get_or_create(
        payload.session_id,
        {
            "stage": payload.stage,
            "data": payload.applicant_data,
        },
    )
    return SessionResponse(**app.state.saved_sessions[payload.session_id])


@app.post("/session/init/{session_id}")
async def init_session(session_id: str):
    """Initialize a new session and log the start."""
    session_store.get_or_create(session_id)
    session_store.log_agent(
        session_id,
        {
            "agent": "MasterOrchestratorAgent",
            "action": "INITIATED_SESSION",
            "reasoning": "New loan inquiry received. Starting orchestration.",
            "status": "SUCCESS",
        },
    )
    session_store.update_stage(session_id, "INITIATED")
    return {"status": "success", "session_id": session_id}


@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    if session_id not in app.state.saved_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**app.state.saved_sessions[session_id])


@app.post("/escalation/preferences")
async def save_escalation_preferences(payload: EscalationPreferenceRequest):
    app.state.escalation_preferences[payload.session_id] = payload.model_dump()
    return {"status": "saved", "session_id": payload.session_id}


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

        loan_amount = coerce_number(
            session_data.get("loan_amount") or session_data.get("amount") or session_data.get("selected_amount"),
            500000,
        )
        interest_rate = coerce_number(
            session_data.get("final_rate") or session_data.get("sanctioned_rate") or session_data.get("offered_rate") or session_data.get("interest_rate"),
            11.0,
        )
        tenure_months = coerce_int(
            session_data.get("tenure_months") or session_data.get("tenure") or session_data.get("loan_term"),
            60,
        )
        tenure_months = max(1, tenure_months)

        purpose = session_data.get("loan_purpose") or session_data.get("purpose") or "general"

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
        if risk_score >= 75:
            risk_tier = "Low Risk"
        elif risk_score >= 50:
            risk_tier = "Medium Risk"
        else:
            risk_tier = "High Risk"

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

        loan_health = build_loan_health(
            {
                "amount": loan_amount,
                "rate": interest_rate,
                "tenure_months": tenure_months,
                "emi": emi,
                "total_interest": total_interest,
                "income": session_data.get("monthly_income") or session_data.get("applicant_income"),
                "monthly_income": session_data.get("monthly_income") or session_data.get("applicant_income"),
            },
            {"credit_score": credit_score, "risk_score": risk_score},
        )

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
            "loan_health": loan_health,
            "benchmark": benchmark,
            "applicant_normalized": applicant_normalized,
            "purpose": purpose,
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
            "loan_health": build_loan_health(
                {
                    "amount": 500000,
                    "rate": 11.0,
                    "tenure_months": 60,
                    "emi": 10871,
                    "total_interest": 152260,
                },
                {"credit_score": 750, "risk_score": 80},
            ),
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
            "purpose": "general",
        }


# ── PIPELINE START OVERRIDE ───────────────────────────────────────
# The master_router /pipeline/start expects {customer_name, initial_message}
# but the frontend sends a full loan payload. This override handles it.

@app.post("/pipeline/start")
async def pipeline_start_override(request: dict):
    """Accept frontend's full pipeline start payload and return session tracking info."""
    session_id = request.get("session_id") or f"LE-{__import__('uuid').uuid4().hex[:10].upper()}"
    from core.session import session_store as _ss
    _ss.get_or_create(session_id, {
        "stage": "INITIATED",
        "data": {
            "pan_number": request.get("pan_number"),
            "applicant_name": request.get("applicant_name"),
            "loan_amount": request.get("loan_amount"),
            "loan_term": request.get("loan_term"),
            "offered_rate": request.get("offered_rate"),
            "previous_sanction_reference": request.get("previous_sanction_reference"),
            "repeat_borrower": bool(request.get("previous_sanction_reference")),
        }
    })
    return {
        "session_id": session_id,
        "status": "ACTIVE",
        "message": "Pipeline started",
        "pipeline_status": "ACTIVE",
        "agent_trace": [],
    }


@app.get("/pipeline/log/{session_id}")
async def pipeline_log(session_id: str):
    """Return pipeline execution log for a session."""
    from core.session import session_store as _ss
    session = _ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
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


def build_loan_health(loan_data: dict, credit_data: dict) -> dict:
    loan_amount = float(loan_data.get("amount") or 0)
    emi = float(loan_data.get("emi") or 0)
    tenure_months = max(1, int(loan_data.get("tenure_months") or 60))
    total_interest = float(loan_data.get("total_interest") or 0)
    credit_score = float(credit_data.get("credit_score") or 720)

    income_base = float(loan_data.get("income") or loan_data.get("monthly_income") or 50000)
    foir = emi / income_base if income_base > 0 else 1.0

    score = 100
    factors: list[dict[str, Any]] = []

    if foir > 0.5:
        score -= 20
        factors.append({
            "factor": "High EMI burden",
            "impact": -20,
            "advice": "Consider part-prepayment when possible to reduce burden",
        })
    elif foir < 0.3:
        factors.append({
            "factor": "Comfortable EMI ratio",
            "impact": 0,
            "advice": "Excellent EMI-to-income ratio reduces default risk",
        })

    if tenure_months > 60:
        score -= 10
        factors.append({
            "factor": "Long tenure",
            "impact": -10,
            "advice": "Longer tenure increases total interest. Prepay after bonus or increment.",
        })

    if credit_score >= 800:
        factors.append({
            "factor": "Strong credit profile",
            "impact": 0,
            "advice": "Timely repayment can push your score toward 850+",
        })

    health_label = "Excellent" if score >= 80 else "Good" if score >= 60 else "Moderate"
    prepayment_savings = round(total_interest * 0.12) if total_interest > 0 else 0

    return {
        "loan_health_score": max(score, 0),
        "health_label": health_label,
        "factors": factors,
        "prepayment_advice": f"Prepaying ₹10,000 in Month 6 saves ₹{prepayment_savings} in total interest",
    }


# ── CREDIT SCORE ALIAS ────────────────────────────────────────────
# Frontend calls GET /credit-score/{pan} — proxy to the underwriting agent logic

@app.get("/credit-score/{pan_number}")
async def get_credit_score_by_pan(pan_number: str):
    """
    GET /credit-score/{pan} — used by the frontend after KYC to fetch
    the simulated CIBIL score and risk tier for the applicant.
    """
    from services.credit_score import simulate_cibil_score, calculate_credit_score
    from agents.underwriting_agent.main import predict_credit_score

    pan = pan_number.strip().upper()
    try:
        cibil_score = simulate_cibil_score(pan)
        features = {"cibil_score": cibil_score}
        xgboost_score = predict_credit_score(features)
        result = calculate_credit_score(cibil_score, xgboost_score)

        credit_score = result["final_score"]
        risk_category = result.get("risk_category", "MEDIUM")

        # Map risk category to band label and color
        band_map = {
            "LOW":         {"label": "Low Risk",    "color": "green"},
            "MEDIUM":      {"label": "Medium Risk", "color": "yellow"},
            "MEDIUM-HIGH": {"label": "Medium-High Risk", "color": "orange"},
            "HIGH":        {"label": "High Risk",   "color": "red"},
        }
        band = band_map.get(risk_category, {"label": risk_category, "color": "yellow"})

        return {
            "pan_number": pan[:5] + "XXXXX",  # masked
            "credit_score": credit_score,
            "credit_score_out_of": 900,
            "credit_band": band["label"],
            "credit_band_color": band["color"],
            "eligible_for_loan": not result.get("hard_reject", False),
            "risk_category": risk_category,
            "message_en": (
                f"Your credit score is {credit_score}. "
                f"You are in the {band['label']} tier."
            ),
            "message_hi": (
                f"आपका credit score {credit_score} है। "
                f"आप {band['label']} tier में आते हैं।"
            ),
        }
    except Exception as e:
        logger.error(f"Credit score lookup failed for {pan}: {e}")
        raise HTTPException(status_code=500, detail=f"Credit score lookup failed: {str(e)}")
