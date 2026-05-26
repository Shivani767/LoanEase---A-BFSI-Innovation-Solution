import json
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

from core.session import session_store
from services.groq_service import GroqService, get_groq_service
from core.config import settings
from agents.prompts import get_system_prompt
from services.conversation_context import build_context_updates, build_memory_prompt_block

logger = logging.getLogger("loanease.master")

router = APIRouter()

# Pydantic models
class PipelineStartRequest(BaseModel):
    customer_name: str
    initial_message: str = "I want to apply for a personal loan"
    language: str = "en"

class PipelineStartResponse(BaseModel):
    session_id: str
    stage: str
    message: str
    next_steps: list[str]

class PipelineStatusRequest(BaseModel):
    session_id: str

class PipelineStatusResponse(BaseModel):
    session_id: str
    stage: str
    progress: Dict[str, Any]
    agent_log: list[Dict[str, Any]]
    next_actions: list[str]

class PipelineProcessRequest(BaseModel):
    session_id: str
    action: str
    data: Optional[Dict[str, Any]] = None

class PipelineProcessResponse(BaseModel):
    session_id: str
    stage: str
    action_result: Dict[str, Any]
    next_stage: Optional[str]
    message: str


def _map_stage_to_prompt_stage(stage: str) -> str:
    stage_upper = (stage or "").upper()
    if stage_upper in {"INITIATED", "PAN_UPLOADED", "AADHAAR_UPLOADED", "KYC_VERIFIED"}:
        return "kyc"
    if stage_upper == "UNDERWRITING_COMPLETE":
        return "credit"
    if stage_upper in {"NEGOTIATION_STARTED", "NEGOTIATION_COMPLETE"}:
        return "negotiation"
    if stage_upper in {"BLOCKCHAIN_VERIFIED", "COMPLETED"}:
        return "sanction"
    return "kyc"


def _build_prompt_context(
    session: Dict[str, Any],
    action: str,
    current_stage: str,
    next_stage: Optional[str],
    action_result: Dict[str, Any],
) -> Dict[str, Any]:
    session_data = session.get("data", {})
    pan_data = session_data.get("pan_data", {})
    aadhaar_data = session_data.get("aadhaar_data", {})
    underwriting_result = session_data.get("underwriting_result", {})
    negotiation_data = session_data.get("negotiation_data", {})
    blockchain_data = session_data.get("blockchain_data", {})
    conversation_context = session_data.get("conversation_context", {}) if isinstance(session_data.get("conversation_context", {}), dict) else {}

    received_docs = []
    if pan_data:
        received_docs.append("PAN")
    if aadhaar_data:
        received_docs.append("Aadhaar")
    if session_data.get("income_proof"):
        received_docs.append("income proof")

    merged_context: Dict[str, Any] = {
        "applicant_name": session_data.get("customer_name", "Applicant"),
        "loan_purpose": conversation_context.get("loan_purpose") or session_data.get("loan_purpose") or "unknown",
        "language": conversation_context.get("language") or session_data.get("language") or "en",
        "stage": current_stage,
        "previous_intent": conversation_context.get("previous_intent") or "UNKNOWN",
        "hesitation_count": conversation_context.get("hesitation_count", 0),
        "negotiation_tone": conversation_context.get("negotiation_tone", "moderate"),
        "questions_asked": conversation_context.get("questions_asked", []),
        "loan_amount": conversation_context.get("loan_amount") or session_data.get("loan_amount") or underwriting_result.get("max_loan", "unknown"),
    }

    merged_context["conversation_memory_block"] = build_memory_prompt_block(merged_context)

    return {
        **merged_context,
        "doc_list": "PAN, Aadhaar, income proof",
        "received_docs": ", ".join(received_docs) if received_docs else "none",
        "verification_status": next_stage or current_stage or "pending",
        "credit_score": underwriting_result.get("credit_score", "N/A"),
        "decision": underwriting_result.get("decision", "manual_review"),
        "sanctioned_amount": underwriting_result.get("max_loan", "N/A"),
        "shap_summary": underwriting_result.get("factors", []),
        "interest_rate": underwriting_result.get("interest_rate", negotiation_data.get("rate", "N/A")),
        "tenure": negotiation_data.get("tenure_months", "N/A"),
        "base_rate": underwriting_result.get("interest_rate", "N/A"),
        "floor_rate": "N/A",
        "approved_amount": underwriting_result.get("max_loan", "N/A"),
        "max_tenure": negotiation_data.get("max_tenure", "N/A"),
        "base_emi": negotiation_data.get("emi", "N/A"),
        "applicant_signals": session_data.get("applicant_signals", []),
        "turn_number": len(session.get("agent_log", [])) + 1,
        "loan_id": blockchain_data.get("reference_id", session.get("id", "N/A")),
        "emi": negotiation_data.get("emi", "N/A"),
        "tx_hash": blockchain_data.get("block_hash", "N/A"),
        "letter_url": blockchain_data.get("letter_url", "N/A"),
        "action": action,
        "action_result": action_result,
    }


async def generate_chat_message(
    groq: GroqService,
    stage: str,
    context: Dict[str, Any],
) -> str:
    """Generate a user-facing message using stage-specific prompts."""
    system_prompt = get_system_prompt(stage, context)
    content = json.dumps(context, ensure_ascii=False)
    message, _trace = await groq.chat(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": content}],
    )
    return message

def create_session(customer_name: str, initial_data: Dict[str, Any]) -> str:
    """Create new session"""
    session_data = {
        "customer_name": customer_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **initial_data
    }
    return session_store.create(session_data)

def get_session_stage_actions(stage: str) -> list[str]:
    """Get available actions for current stage"""
    stage_actions = {
        "INITIATED": ["upload_pan", "start_chat"],
        "PAN_UPLOADED": ["upload_aadhaar", "extract_pan"],
        "AADHAAR_UPLOADED": ["verify_kyc"],
        "KYC_VERIFIED": ["assess_credit"],
        "UNDERWRITING_COMPLETE": ["start_negotiation"],
        "NEGOTIATION_STARTED": ["negotiate_rate", "accept_offer"],
        "NEGOTIATION_COMPLETE": ["generate_sanction"],
        "BLOCKCHAIN_VERIFIED": ["complete"],
        "COMPLETED": []
    }
    return stage_actions.get(stage, [])

def get_stage_progress(stage: str) -> Dict[str, Any]:
    """Get progress information for stage"""
    progress_stages = [
        "INITIATED",
        "PAN_UPLOADED", 
        "AADHAAR_UPLOADED",
        "KYC_VERIFIED",
        "UNDERWRITING_COMPLETE",
        "NEGOTIATION_COMPLETE",
        "BLOCKCHAIN_VERIFIED",
        "COMPLETED"
    ]
    
    current_index = progress_stages.index(stage) if stage in progress_stages else 0
    total_stages = len(progress_stages)
    
    return {
        "current_stage": stage,
        "current_index": current_index,
        "total_stages": total_stages,
        "progress_percentage": (current_index / (total_stages - 1)) * 100 if total_stages > 1 else 0,
        "completed_stages": progress_stages[:current_index],
        "remaining_stages": progress_stages[current_index + 1:]
    }

@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(
    request: PipelineStartRequest,
    groq: GroqService = Depends(get_groq_service),
):
    """Start loan application pipeline"""
    try:
        # Create session
        session_id = create_session(request.customer_name, {
            "initial_message": request.initial_message,
            "language": request.language
        })
        initial_context = build_context_updates(request.initial_message, {"applicant_name": request.customer_name, "language": request.language}, "INITIATED")
        session_store.update_data(session_id, "conversation_context", initial_context)
        
        # Get next actions
        next_actions = get_session_stage_actions("INITIATED")
        
        # Update session
        session_store.update_stage(session_id, "INITIATED")
        session_store.log_agent(session_id, {
            "agent": "master",
            "action": "pipeline_start",
            "customer_name": request.customer_name,
            "language": request.language
        })
        
        message = await generate_chat_message(
            groq,
            stage="kyc",
            context={
                "applicant_name": request.customer_name,
                "loan_purpose": initial_context.get("loan_purpose", "unknown"),
                "language": initial_context.get("language", request.language),
                "questions_asked": initial_context.get("questions_asked", []),
                "negotiation_tone": initial_context.get("negotiation_tone", "moderate"),
                "doc_list": "PAN, Aadhaar, income proof",
                "received_docs": "none",
                "verification_status": "INITIATED",
                "conversation_memory_block": build_memory_prompt_block(initial_context),
            },
        )

        return PipelineStartResponse(
            session_id=session_id,
            stage="INITIATED",
            message=message,
            next_steps=next_actions,
        )
        
    except Exception as e:
        logger.error(f"Pipeline start error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline start failed: {str(e)}")

@router.post("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(request: PipelineStatusRequest):
    """Get current pipeline status"""
    try:
        # Get session
        session = session_store.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get progress
        progress = get_stage_progress(session["stage"])
        
        # Get next actions
        next_actions = get_session_stage_actions(session["stage"])
        
        return PipelineStatusResponse(
            session_id=request.session_id,
            stage=session["stage"],
            progress=progress,
            agent_log=session["agent_log"],
            next_actions=next_actions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline status error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline status failed: {str(e)}")

@router.post("/process", response_model=PipelineProcessResponse)
async def process_pipeline_action(
    request: PipelineProcessRequest,
    groq: GroqService = Depends(get_groq_service),
):
    """Process pipeline action"""
    try:
        # Get session
        session = session_store.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        current_stage = session["stage"]
        action_result = {}
        next_stage = None
        message = ""
        
        # Process action based on current stage
        if request.action == "upload_pan":
            if request.data and "pan_data" in request.data:
                session_store.update_data(request.session_id, "pan_data", request.data["pan_data"])
                session_store.update_stage(request.session_id, "PAN_UPLOADED")
                next_stage = "PAN_UPLOADED"
                action_result = {"status": "success", "data": request.data["pan_data"]}
            else:
                action_result = {"status": "error", "message": "PAN data required"}
        
        elif request.action == "upload_aadhaar":
            if request.data and "aadhaar_data" in request.data:
                session_store.update_data(request.session_id, "aadhaar_data", request.data["aadhaar_data"])
                session_store.update_stage(request.session_id, "AADHAAR_UPLOADED")
                next_stage = "AADHAAR_UPLOADED"
                action_result = {"status": "success", "data": request.data["aadhaar_data"]}
            else:
                action_result = {"status": "error", "message": "Aadhaar data required"}
        
        elif request.action == "verify_kyc":
            # KYC verification would be handled by KYC agent
            if request.data and "kyc_result" in request.data:
                kyc_result = request.data["kyc_result"]
                if kyc_result.get("overall_kyc_passed"):
                    session_store.update_stage(request.session_id, "KYC_VERIFIED")
                    next_stage = "KYC_VERIFIED"
                action_result = {"status": "success", "data": kyc_result}
            else:
                action_result = {"status": "error", "message": "KYC result required"}
        
        elif request.action == "assess_credit":
            # Credit assessment would be handled by underwriting agent
            if request.data and "underwriting_result" in request.data:
                underwriting_result = request.data["underwriting_result"]
                session_store.update_data(request.session_id, "underwriting_result", underwriting_result)
                if underwriting_result.get("decision") == "APPROVED":
                    session_store.update_stage(request.session_id, "UNDERWRITING_COMPLETE")
                    next_stage = "UNDERWRITING_COMPLETE"
                action_result = {"status": "success", "data": underwriting_result}
            else:
                action_result = {"status": "error", "message": "Underwriting result required"}
        
        elif request.action == "start_negotiation":
            if request.data and "negotiation_data" in request.data:
                session_store.update_data(request.session_id, "negotiation_data", request.data["negotiation_data"])
                session_store.update_stage(request.session_id, "NEGOTIATION_STARTED")
                next_stage = "NEGOTIATION_STARTED"
                action_result = {"status": "success", "data": request.data["negotiation_data"]}
            else:
                action_result = {"status": "error", "message": "Negotiation data required"}
        
        elif request.action == "complete_negotiation":
            if request.data and "final_rate" in request.data:
                session_store.update_data(request.session_id, "negotiation_data", request.data)
                session_store.update_stage(request.session_id, "NEGOTIATION_COMPLETE")
                next_stage = "NEGOTIATION_COMPLETE"
                action_result = {"status": "success", "data": request.data}
            else:
                action_result = {"status": "error", "message": "Final rate required"}
        
        elif request.action == "generate_sanction":
            if request.data and "blockchain_data" in request.data:
                session_store.update_data(request.session_id, "blockchain_data", request.data["blockchain_data"])
                session_store.update_stage(request.session_id, "BLOCKCHAIN_VERIFIED")
                next_stage = "BLOCKCHAIN_VERIFIED"
                action_result = {"status": "success", "data": request.data["blockchain_data"]}
            else:
                action_result = {"status": "error", "message": "Blockchain data required"}
        
        elif request.action == "complete":
            session_store.update_stage(request.session_id, "COMPLETED")
            next_stage = "COMPLETED"
            action_result = {"status": "success"}
        else:
            action_result = {"status": "error", "message": "unknown_action"}

        refreshed_session = session_store.get(request.session_id) or session
        prompt_stage = _map_stage_to_prompt_stage(next_stage or current_stage)
        prompt_context = _build_prompt_context(
            refreshed_session,
            request.action,
            current_stage,
            next_stage,
            action_result,
        )

        session_context = refreshed_session.get("data", {}).get("conversation_context", {})
        if not isinstance(session_context, dict):
            session_context = {}
        user_message = request.data.get("user_message", "").strip() if request.data else ""
        if user_message:
            derived = build_context_updates(user_message, {**session_context, **prompt_context}, current_stage)
            session_context.update(derived)
            session_context["conversation_memory_block"] = build_memory_prompt_block(session_context)
            session_store.update_data(request.session_id, "conversation_context", session_context)
            prompt_context.update(session_context)

        message = await generate_chat_message(
            groq,
            stage=prompt_stage,
            context=prompt_context,
        )
        
        # Log action
        session_store.log_agent(request.session_id, {
            "agent": "master",
            "action": request.action,
            "result": action_result,
            "next_stage": next_stage
        })
        
        return PipelineProcessResponse(
            session_id=request.session_id,
            stage=session["stage"],
            action_result=action_result,
            next_stage=next_stage,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline process error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline process failed: {str(e)}")

@router.get("/health")
async def pipeline_health():
    """Pipeline service health check"""
    return {
        "status": "healthy",
        "active_sessions": len(session_store._sessions),
        "session_ttl_hours": settings.SESSION_TTL_HOURS
    }
