from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssessRequest(BaseModel):
    pan_number: str = Field(..., description="PAN number (ABCDE1234F)", examples=["ABCDE1234F"])
    gender: str = Field(..., examples=["Male"])
    married: str = Field(..., examples=["Yes"])
    dependents: str = Field(..., examples=["1"])
    education: str = Field(..., examples=["Graduate"])
    self_employed: str = Field(..., examples=["No"])
    applicant_income: float = Field(..., ge=0)
    coapplicant_income: float = Field(..., ge=0)
    loan_amount: float = Field(..., ge=0)
    loan_amount_term: float = Field(..., ge=0)
    credit_history: float = Field(..., ge=0)
    property_area: str = Field(..., examples=["Urban"])
    preferred_language: Literal["en", "hi"] = Field(default="en", description="Preferred language for messages")


class AssessResponse(BaseModel):
    application_id: str
    decision: Literal["APPROVED", "APPROVED_WITH_CONDITIONS", "CONDITIONAL_REJECT", "REJECTED"]
    credit_score: int
    cibil_score: int | None = None
    cibil_band: str | None = None
    cibil_classification: str | None = None
    risk_label: str | None = None
    industry_standard: str | None = None
    eligible: bool | None = None
    conditional: bool | None = None
    rate_range: str | None = None
    max_negotiation_rounds: int | None = None
    credit_score_out_of: int = 900
    credit_band: str
    credit_band_color: Literal["green", "yellow", "orange", "red"]
    risk_score: int
    risk_score_out_of: int = 100
    approval_probability: float
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    confidence_width: float | None = None
    model_certainty: Literal["HIGH", "MEDIUM", "LOW"] | None = None
    risk_tier: Literal["Low Risk", "Medium Risk", "High Risk"]
    offered_rate: float = Field(..., description="Interest rate offered based on credit band")
    rate_range: dict = Field(..., description="Min/max rates for credit band")
    negotiation_allowed: bool
    max_negotiation_rounds: int
    xgboost_probability: float
    xgboost_ran: bool
    shap_explanation: list[str]
    structured_shap_narration: str | None = None
    threshold_used: float
    income_reasonability: dict | None = None
    soft_reject_guidance: dict | None = None
    model_drift_warning: bool = False
    drifted_features: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    confidence_message: str | None = None


class ExplainResponse(BaseModel):
    application_id: str
    decision: str
    approval_probability: float
    risk_tier: str
    risk_score: int
    threshold_used: float
    raw_input: dict
    top_explanations: list[str]
    shap_waterfall: list[dict]
    structured_shap_narration: str | None = None
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    confidence_width: float | None = None
    model_certainty: str | None = None
    income_reasonability: dict | None = None
    soft_reject_guidance: dict | None = None
    confidence_message: str | None = None


class CreditScoreResponse(BaseModel):
    pan_number: str = Field(..., description="Masked PAN (first 5 + last 1 char)")
    credit_score: int
    credit_score_out_of: int = 900
    credit_band: str
    credit_band_color: Literal["green", "yellow", "orange", "red"]
    eligible_for_loan: bool
    score_breakdown: dict = Field(
        default={
            "high_risk_low_score": "0-300",
            "medium_risk_intermediate_score": "301-699",
            "low_risk_high_score": "700-900",
        }
    )
    applicant_score_falls_in: str
    message_en: str
    message_hi: str
    minimum_required_score: int = 0
    shortfall: int | None = None
    improvement_tips: list[str] | None = None
    earliest_reapply: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_version: str
    accuracy: float
    uptime_seconds: int
    model_drift_warning: bool = False
    drifted_features: list[str] = Field(default_factory=list)
    recommendation: str | None = None


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
    preferred_time: str  # "Morning", "Afternoon", "Evening"
    whatsapp_opt_in: bool


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    language: str = "en"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    language: str


class PipelineStartRequest(BaseModel):
    session_id: str
    applicant_name: str
    pan_number: str
    loan_amount: float
    loan_term: int
    offered_rate: float
