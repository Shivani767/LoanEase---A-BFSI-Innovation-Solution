from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import LoanPipeline

app = FastAPI(title="LoanEase Pipeline API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = LoanPipeline()
running_tasks: dict[str, asyncio.Task] = {}


class PipelineStartRequest(BaseModel):
    session_id: str | None = None
    applicant_name: str = "Applicant"
    pan_number: str = "ABCDE1234F"
    aadhaar_number: str = "123456789012"
    applicant_income: float = Field(75000, ge=0)
    loan_amount: int = Field(500000, ge=0)
    loan_term: int = Field(60, ge=1)
    offered_rate: float = 11.5
    risk_tier: str = "Low Risk"
    max_negotiation_rounds: int = 3
    negotiation_requested: bool = True
    counter_rate: float | None = 11.0


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "pipeline", "port": 8004}


@app.post("/pipeline/start")
async def start_pipeline(request: PipelineStartRequest) -> dict:
    payload = request.model_dump()
    session_id = payload.get("session_id") or str(uuid4())
    payload["session_id"] = session_id

    if session_id in running_tasks and not running_tasks[session_id].done():
        return {"session_id": session_id, "status": "ACTIVE", "message": "Pipeline already running"}

    running_tasks[session_id] = asyncio.create_task(pipeline.run_full_pipeline(payload))
    return {"session_id": session_id, "status": "ACTIVE", "message": "Pipeline started"}


@app.get("/pipeline/log/{session_id}")
def get_pipeline_log(session_id: str) -> dict:
    log = pipeline.get_session_log(session_id)
    if not log.get("agent_trace"):
        raise HTTPException(status_code=404, detail="Session not found")
    return log

