# All Pydantic models for unified API
# Note: Individual agent files contain their own models
# This file can be used for shared models across agents

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class ErrorResponse(BaseResponse):
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: int
    timestamp: datetime = datetime.utcnow()

class SessionCreateRequest(BaseModel):
    customer_name: str
    initial_data: Optional[Dict[str, Any]] = {}

class SessionCreateResponse(BaseModel):
    session_id: str
    stage: str
    expires_at: datetime

# Shared KYC models
class DocumentUploadRequest(BaseModel):
    session_id: str
    language: str = "en"

class KYCVerificationRequest(BaseModel):
    session_id: str

# Shared underwriting models
class LoanApplicationRequest(BaseModel):
    session_id: str
    loan_amount: float
    tenure_years: int
    purpose: Optional[str] = "Personal Loan"

# Shared negotiation models
class RateNegotiationRequest(BaseModel):
    session_id: str
    proposed_rate: float
    negotiation_id: str

# Shared blockchain models
class DocumentVerificationRequest(BaseModel):
    reference_id: str

class PipelineRequest(BaseModel):
    session_id: str
    action: str
    data: Optional[Dict[str, Any]] = None

class PipelineResponse(BaseModel):
    session_id: str
    stage: str
    action_result: Dict[str, Any]
    next_stage: Optional[str] = None
    message: str
