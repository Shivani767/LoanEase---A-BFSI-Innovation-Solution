"""
FastAPI endpoints for LoanEase Agent Orchestration System.
Exposes the 5-agent orchestration via REST API.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

from agents import (
    LoanEaseOrchestrator,
    AgentResult,
    AgentStatus,
)

# Initialize orchestrator
orchestrator = LoanEaseOrchestrator()

# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AgentWorkflowRequest(BaseModel):
    """Request model for running complete agent workflow."""
    pan_number: str = Field(..., description="Applicant's PAN number")
    aadhaar_number: Optional[str] = Field(None, description="Applicant's Aadhaar number")
    applicant_income: float = Field(..., ge=0, description="Monthly applicant income")
    coapplicant_income: float = Field(0, ge=0, description="Co-applicant income")
    loan_amount: float = Field(..., ge=0, description="Requested loan amount")
    loan_term: float = Field(..., ge=0, description="Loan tenure in months")
    credit_history: float = Field(1.0, ge=0, description="Credit history length (years)")
    preferred_language: Literal["en", "hi"] = Field("en", description="Preferred language")
    negotiation_requested: bool = Field(False, description="Whether to run negotiation")
    counter_rate: Optional[float] = Field(None, description="Counter-offer rate for negotiation")


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    name: str
    role: str
    tools: list[str]
    available: bool


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""
    session_id: str
    status: str
    reasoning: str
    duration_ms: int
    agents_executed: list[str]
    application_summary: dict
    next_steps: list[str]
    workflow_history: list[dict]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/", summary="List all agents")
async def list_agents() -> list[dict]:
    """
    List all available agents in the orchestration system.
    """
    return orchestrator.list_agents()


@router.get("/{agent_name}/status", summary="Get agent status")
async def get_agent_status(agent_name: str) -> AgentStatusResponse:
    """
    Get the status and capabilities of a specific agent.
    """
    status = orchestrator.get_agent_status(agent_name)
    if not status.get("available", False):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return AgentStatusResponse(**status)


@router.post("/workflow", summary="Run complete workflow")
async def run_workflow(request: AgentWorkflowRequest) -> WorkflowResponse:
    """
    Run the complete 5-agent orchestration workflow.
    
    This endpoint coordinates:
    1. KYC Agent - Document verification
    2. Underwriting Agent - Credit assessment
    3. Negotiation Agent - Rate negotiation
    4. Translation Agent - Multilingual support
    5. Orchestrator Agent - Workflow management
    """
    try:
        # Convert request to workflow input
        workflow_input = {
            "pan_number": request.pan_number,
            "aadhaar_number": request.aadhaar_number,
            "applicant_income": request.applicant_income,
            "coapplicant_income": request.coapplicant_income,
            "loan_amount": request.loan_amount,
            "loan_term": request.loan_term,
            "credit_history": request.credit_history,
            "preferred_language": request.preferred_language,
            "negotiation_requested": request.negotiation_requested,
            "counter_rate": request.counter_rate,
        }
        
        # Run workflow
        result = orchestrator.run_workflow(workflow_input)
        
        # Extract workflow history
        history = result.output.get("workflow_history", [])
        agents_executed = [h.get("agent_name") for h in history]
        
        return WorkflowResponse(
            session_id=result.output.get("session_id", ""),
            status=result.status.value,
            reasoning=result.reasoning,
            duration_ms=result.duration_ms,
            agents_executed=agents_executed,
            application_summary=result.output.get("application_summary", {}),
            next_steps=result.output.get("next_steps", []),
            workflow_history=history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/{session_id}", summary="Get workflow status")
async def get_workflow_status(session_id: str) -> dict:
    """
    Get the status of a previously submitted workflow.
    """
    # In production, this would fetch from persistent storage
    return {
        "session_id": session_id,
        "status": "not_implemented",
        "message": "Session lookup not yet implemented"
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", summary="Health check")
async def health_check() -> dict:
    """
    Check if the agent orchestration system is healthy.
    """
    agents = orchestrator.list_agents()
    return {
        "status": "healthy",
        "agents_count": len(agents),
        "agents": [a["name"] for a in agents]
    }