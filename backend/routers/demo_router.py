"""
Demo-specific API endpoints for LoanEase BTech evaluation.

GET  /demo/start  – create a pre-filled session for clean demo start
POST /demo/reset  – wipe all sessions + blockchain for a fresh demo run
GET  /demo/config  – expose demo_mode flag to the frontend
"""

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.config import settings
from core.session import session_store
from blockchain import ledger

logger = logging.getLogger("loanease.demo")

router = APIRouter()


# ── GET /demo/start ─────────────────────────────────────────────────
@router.get("/start")
async def demo_start():
    """Create a session pre-filled with demo applicant data."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is not enabled")

    session_id = str(uuid.uuid4())[:8].upper()
    demo_data = {
        "stage": "INITIATED",
        "data": {
            "customer_name": "Rahul Sharma",
            "loan_amount": 500000,
            "language": "en",
        },
        "agent_log": [],
    }
    session_store.get_or_create(session_id, demo_data)

    logger.info("🎯 Demo session created: %s", session_id)
    return {
        "session_id": session_id,
        "applicant_name": "Rahul Sharma",
        "loan_amount": 500000,
        "stage": "INITIATED",
        "message": "Demo session ready. Upload a PAN card to begin.",
    }


# ── POST /demo/reset ────────────────────────────────────────────────
class ResetPayload(BaseModel):
    confirm: str


@router.post("/reset")
async def demo_reset(payload: ResetPayload, request: Request):
    """Clear all sessions and reset blockchain to genesis block."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is not enabled")

    if payload.confirm != "RESET_LOANEASE_DEMO":
        raise HTTPException(status_code=400, detail="Invalid reset confirmation string")

    sessions_cleared = session_store.clear_all()
    blocks_cleared = ledger.reset_to_genesis()

    # Also clear the saved_sessions dict on app state if it exists
    saved_sessions: Dict[str, Any] = getattr(request.app.state, "saved_sessions", {})
    saved_count = len(saved_sessions)
    saved_sessions.clear()

    logger.info(
        "♻️ Demo reset: %d sessions cleared, %d blocks cleared",
        sessions_cleared + saved_count,
        blocks_cleared,
    )

    return {
        "status": "reset_complete",
        "sessions_cleared": sessions_cleared + saved_count,
        "blockchain_reset": True,
        "blocks_cleared": blocks_cleared,
        "message": "LoanEase demo environment reset. Ready for fresh demo.",
    }


# ── GET /demo/config ─────────────────────────────────────────────────
@router.get("/config")
async def demo_config():
    """Expose demo mode flag and basic config to the frontend."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "demo_pan_numbers": {
            "approval": "DEMO00000D (score 820)",
            "conditional": "DEMO11111E (score 650)",
            "rejection": "DEMO22222F (score 285)",
        },
    }
