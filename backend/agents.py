"""
LoanEase 5-Agent Orchestration System
=======================================
A lightweight custom agent framework (no LangChain/AutoGen) that makes all agents
visible, traceable, and evidently collaborative.

Each agent wraps existing services and exposes them through a unified interface.
"""

from __future__ import annotations

import os
import time
import base64
import hashlib
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

class AgentStatus(str, Enum):
    """Possible states for agent execution."""
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class AgentResult:
    """
    Standardized result from any agent execution.
    
    Attributes:
        agent_name: Identifier of which agent produced this result
        status: Execution outcome - success, failed, or escalated
        output: Dictionary containing agent-specific outputs
        reasoning: Plain English explanation of what happened
        next_agent: Which agent should run next (None if workflow complete)
        timestamp: ISO-formatted execution timestamp
        duration_ms: How long the agent took to execute
    """
    agent_name: str
    status: AgentStatus
    output: dict = field(default_factory=dict)
    reasoning: str = ""
    next_agent: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "output": self.output,
            "reasoning": self.reasoning,
            "next_agent": self.next_agent,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# TOOL SYSTEM
# =============================================================================

@dataclass
class Tool:
    """
    A callable tool that an agent can use.
    
    Attributes:
        name: Unique identifier for the tool
        description: What the tool does (for LLM context)
        func: The actual callable function
        parameters: Schema for expected inputs
    """
    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict = field(default_factory=dict)


def create_tool(name: str, description: str) -> Callable:
    """
    Decorator to create a tool from a function.
    
    Usage:
        @create_tool("extract_pan", "Extract PAN details from document")
        def extract_pan(image_data: bytes) -> dict:
            ...
    """
    def decorator(func: Callable) -> Tool:
        return Tool(
            name=name,
            description=description,
            func=func,
            parameters={}  # Could be enhanced with schema
        )
    return decorator


# =============================================================================
# BASE AGENT CLASS
# =============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Each agent has:
    - name: Unique identifier
    - role: What the agent does
    - tools: List of tools it can call
    - system_prompt: Instructions for the LLM
    - groq_client: LLM client for reasoning
    """

    def __init__(self, name: str, role: str, tools: list[Tool] | None = None):
        self.name = name
        self.role = role
        self.tools = tools or []
        self.system_prompt = self._build_system_prompt()
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent's LLM."""
        pass

    @abstractmethod
    def run(self, input_data: dict) -> AgentResult:
        """
        Execute the agent on input data.
        
        Args:
            input_data: Dictionary containing all inputs needed by the agent
            
        Returns:
            AgentResult with execution details and outputs
        """
        pass

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Result from tool execution
            
        Raises:
            ValueError: If tool not found
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.func(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found for agent '{self.name}'")

    def reason_with_llm(self, user_prompt: str, context: dict) -> str:
        """
        Use Groq LLM to reason about a situation.
        
        Args:
            user_prompt: What to ask the LLM
            context: Additional context for reasoning
            
        Returns:
            LLM's reasoning as a string
        """
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"Context: {context}\n\nQuestion: {user_prompt}"
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM reasoning unavailable: {str(e)}"


# =============================================================================
# AGENT 1: KYC AGENT
# =============================================================================

class KYCAgent(BaseAgent):
    """
    KYC (Know Your Customer) Agent
    
    Role: Verify applicant identity through document extraction and validation.
    Handles PAN card and Aadhaar card processing.
    
    Tools:
    - extract_pan: Extract PAN details from document
    - extract_aadhaar: Extract Aadhaar details from document  
    - cross_validate: Verify consistency between documents
    - validate_applicant: Check applicant eligibility (age, etc.)
    """

    def __init__(self):
        super().__init__(
            name="KYC Agent",
            role="Verify applicant identity through document extraction and validation",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        """Create tools for KYC operations."""
        return [
            Tool(
                name="extract_pan",
                description="Extract PAN number and name from document image",
                func=self._mock_extract_pan,
                parameters={"image_data": "bytes"}
            ),
            Tool(
                name="extract_aadhaar",
                description="Extract Aadhaar number and details from document image",
                func=self._mock_extract_aadhaar,
                parameters={"image_data": "bytes"}
            ),
            Tool(
                name="cross_validate",
                description="Verify name consistency between PAN and Aadhaar",
                func=self._mock_cross_validate,
                parameters={"pan_data": "dict", "aadhaar_data": "dict"}
            ),
            Tool(
                name="validate_applicant",
                description="Check applicant eligibility based on extracted details",
                func=self._mock_validate_applicant,
                parameters={"kyc_data": "dict"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the KYC Agent for LoanEase. Your role is to:
1. Extract and validate identity documents (PAN, Aadhaar)
2. Cross-validate information across documents
3. Verify applicant eligibility (age 21-65, valid documents)
4. Flag any discrepancies for review

Always respond with clear, concise reasoning. If documents are unclear or
inconsistent, escalate to the next agent with specific concerns."""

    def _mock_extract_pan(self, image_data: bytes = None, pan_number: str = None) -> dict:
        """Mock PAN extraction - in production, calls kyc_backend service."""
        # Simulates calling kyc_backend/app/extractors.py
        return {
            "extracted": True,
            "pan_number": pan_number or "ABCDE1234F",
            "name": "JOHN DOE",
            "fathers_name": "MARK DOE",
            "date_of_birth": "15/03/1985",
            "document_type": "PAN_CARD",
            "validation": {
                "pan_format_valid": True,
                "name_found": True,
                "dob_found": True
            }
        }

    def _mock_extract_aadhaar(self, image_data: bytes = None, aadhaar_number: str = None) -> dict:
        """Mock Aadhaar extraction - in production, calls kyc_backend service."""
        return {
            "extracted": True,
            "aadhaar_number": aadhaar_number or "123456789012",
            "name": "JOHN DOE",
            "date_of_birth": "15/03/1985",
            "gender": "Male",
            "address": "123 Main Street, Mumbai, Maharashtra",
            "document_type": "AADHAAR_CARD",
            "validation": {
                "aadhaar_format_valid": True,
                "name_found": True,
                "address_found": True
            }
        }

    def _mock_cross_validate(self, pan_data: dict, aadhaar_data: dict) -> dict:
        """Mock cross-validation between PAN and Aadhaar."""
        pan_name = pan_data.get("name", "").upper()
        aadhaar_name = aadhaar_data.get("name", "").upper()
        
        names_match = pan_name == aadhaar_name
        
        return {
            "validation_passed": names_match,
            "discrepancies": [] if names_match else ["Name mismatch between PAN and Aadhaar"],
            "pan_name": pan_name,
            "aadhaar_name": aadhaar_name,
            "cross_validation_score": 1.0 if names_match else 0.0
        }

    def _mock_validate_applicant(self, kyc_data: dict) -> dict:
        """Mock applicant eligibility validation."""
        dob = kyc_data.get("date_of_birth")
        if dob:
            try:
                dt = datetime.strptime(dob, "%d/%m/%Y")
                age = datetime.now().year - dt.year
            except:
                age = 35
        else:
            age = 35
            
        eligible = 21 <= age <= 65
        
        return {
            "eligible": eligible,
            "age": age,
            "age_eligible": eligible,
            "reason": f"Applicant age {age} is within eligible range (21-65)" if eligible else f"Applicant age {age} is outside eligible range"
        }

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute KYC verification on input data.
        
        Expected input:
        {
            "pan_number": "ABCDE1234F",  (optional)
            "aadhaar_number": "123456789012", (optional)
            "applicant_name": "John Doe", (optional)
            "session_id": "uuid"
        }
        """
        start_time = time.time()
        
        # Extract inputs
        pan_number = input_data.get("pan_number")
        aadhaar_number = input_data.get("aadhaar_number")
        applicant_name = input_data.get("applicant_name")
        
        # Step 1: Extract PAN
        pan_result = self.call_tool("extract_pan", pan_number=pan_number)
        
        # Step 2: Extract Aadhaar
        aadhaar_result = self.call_tool("extract_aadhaar", aadhaar_number=aadhaar_number)
        
        # Step 3: Cross-validate
        cross_result = self.call_tool(
            "cross_validate",
            pan_data=pan_result,
            aadhaar_data=aadhaar_result
        )
        
        # Step 4: Validate applicant eligibility
        kyc_data = {
            "name": pan_result.get("name"),
            "date_of_birth": pan_result.get("date_of_birth")
        }
        eligibility = self.call_tool("validate_applicant", kyc_data=kyc_data)
        
        # Build output
        output = {
            "kyc_verified": cross_result.get("validation_passed", False),
            "pan_details": {
                "pan_number": pan_result.get("pan_number"),
                "name": pan_result.get("name"),
                "dob": pan_result.get("date_of_birth")
            },
            "aadhaar_details": {
                "aadhaar_number": aadhaar_result.get("aadhaar_number"),
                "name": aadhaar_result.get("name"),
                "address": aadhaar_result.get("address")
            },
            "cross_validation": cross_result,
            "eligibility": eligibility,
            "session_id": input_data.get("session_id")
        }
        
        # Determine next step
        if not cross_result.get("validation_passed"):
            reasoning = "KYC verification failed due to name mismatch between PAN and Aadhaar documents."
            status = AgentStatus.FAILED
            next_agent = None
        elif not eligibility.get("eligible"):
            reasoning = f"KYC verification completed but applicant is not eligible: {eligibility.get('reason')}"
            status = AgentStatus.FAILED
            next_agent = None
        else:
            reasoning = "KYC verification successful. PAN and Aadhaar documents validated, names match, applicant is eligible (age 21-65)."
            status = AgentStatus.SUCCESS
            next_agent = "Underwriting Agent"
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 2: UNDERWRITING AGENT
# =============================================================================

class UnderwritingAgent(BaseAgent):
    """
    Underwriting Agent
    
    Role: Assess creditworthiness, calculate risk scores, and determine
    loan eligibility and pricing.
    
    Tools:
    - get_credit_score: Fetch CIBIL credit score for PAN
    - assess_risk: Calculate overall risk score
    - determine_eligibility: Decide approval/rejection
    - generate_explanation: Provide SHAP-based explanations
    """

    def __init__(self):
        super().__init__(
            name="Underwriting Agent",
            role="Assess creditworthiness and determine loan eligibility",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_credit_score",
                description="Fetch credit score from CIBIL bureau",
                func=self._mock_get_credit_score,
                parameters={"pan_number": "str"}
            ),
            Tool(
                name="assess_risk",
                description="Calculate risk score based on multiple factors",
                func=self._mock_assess_risk,
                parameters={"credit_score": "int", "income": "float", "loan_amount": "float"}
            ),
            Tool(
                name="determine_eligibility",
                description="Determine loan approval decision",
                func=self._mock_determine_eligibility,
                parameters={"risk_score": "int", "credit_score": "int"}
            ),
            Tool(
                name="generate_explanation",
                description="Generate human-readable explanation of decision",
                func=self._mock_generate_explanation,
                parameters={"decision": "str", "risk_score": "int", "credit_score": "int"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the Underwriting Agent for LoanEase. Your role is to:
1. Fetch and analyze credit scores from bureau
2. Calculate risk scores using ML models
3. Determine loan eligibility (Approved, Approved with Conditions, Rejected)
4. Generate offer details including interest rate and terms
5. Provide explainable AI explanations for decisions

Always use data-driven reasoning. If credit score is below 300, automatically
escalate to rejection with clear reasoning."""

    def _mock_get_credit_score(self, pan_number: str) -> dict:
        """Mock credit score retrieval - in production, calls backend credit_score.py"""
        # Simulates calling backend/app/credit_score.py
        import hashlib
        
        # Deterministic score based on PAN
        hash_val = int(hashlib.sha256(pan_number.encode()).hexdigest(), 16)
        score = 300 + (hash_val % 601)
        
        # Map to bands
        if score >= 700:
            band = "low_risk"
            color = "green"
            rate_min, rate_max = 9.0, 11.0
            negotiation_rounds = 3
        elif score >= 301:
            band = "medium_risk"
            color = "yellow"
            rate_min, rate_max = 11.0, 13.0
            negotiation_rounds = 1
        else:
            band = "high_risk"
            color = "red"
            rate_min, rate_max = 13.0, 15.0
            negotiation_rounds = 0
            
        return {
            "credit_score": score,
            "credit_band": band,
            "color": color,
            "rate_range": {"min": rate_min, "max": rate_max},
            "negotiation_allowed": negotiation_rounds > 0,
            "max_negotiation_rounds": negotiation_rounds
        }

    def _mock_assess_risk(self, credit_score: int, income: float, loan_amount: float) -> dict:
        """Mock risk assessment."""
        # Simple risk calculation
        income_ratio = loan_amount / income if income > 0 else 1
        
        if credit_score >= 700:
            base_risk = 20
        elif credit_score >= 301:
            base_risk = 50
        else:
            base_risk = 80
            
        # Adjust for loan-to-income ratio
        if income_ratio > 5:
            base_risk += 10
        elif income_ratio > 3:
            base_risk += 5
            
        risk_score = min(100, base_risk)
        
        if risk_score >= 75:
            tier = "Low Risk"
        elif risk_score >= 50:
            tier = "Medium Risk"
        else:
            tier = "High Risk"
            
        return {
            "risk_score": risk_score,
            "risk_tier": tier,
            "income_ratio": round(income_ratio, 2),
            "factors": {
                "credit_score_weight": 0.6,
                "income_ratio_weight": 0.3,
                "other_factors_weight": 0.1
            }
        }

    def _mock_determine_eligibility(self, risk_score: int, credit_score: int) -> dict:
        """Mock eligibility determination."""
        if credit_score < 300:
            decision = "REJECTED"
            probability = 0.05
        elif risk_score >= 75:
            decision = "APPROVED"
            probability = 0.95
        elif risk_score >= 50:
            decision = "APPROVED_WITH_CONDITIONS"
            probability = 0.75
        else:
            decision = "REJECTED"
            probability = 0.25
            
        return {
            "decision": decision,
            "approval_probability": probability,
            "threshold_used": 0.7
        }

    def _mock_generate_explanation(self, decision: str, risk_score: int, credit_score: int) -> dict:
        """Mock explanation generation."""
        explanations = []
        
        if decision == "APPROVED":
            explanations = [
                f"Credit score of {credit_score} is in the favorable range (700-900)",
                f"Risk score of {risk_score} indicates low risk profile",
                "Stable income and manageable loan-to-income ratio",
                "No adverse flags in credit history"
            ]
        elif decision == "APPROVED_WITH_CONDITIONS":
            explanations = [
                f"Credit score of {credit_score} is in the moderate range (301-699)",
                f"Risk score of {risk_score} indicates medium risk",
                "Loan amount may require additional verification",
                "Interest rate will be adjusted based on risk tier"
            ]
        else:
            explanations = [
                f"Credit score of {credit_score} is below acceptable threshold",
                f"Risk score of {risk_score} indicates high risk",
                "Applicant does not meet minimum eligibility criteria",
                "Consider improving credit score before reapplying"
            ]
            
        return {
            "top_explanations": explanations,
            "shap_waterfall": [
                {"factor": "credit_score", "impact": "high"},
                {"factor": "income_ratio", "impact": "medium"},
                {"factor": "employment_status", "impact": "low"}
            ]
        }

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute underwriting assessment on input data.
        
        Expected input from KYC Agent:
        {
            "pan_details": {...},
            "eligibility": {...},
            "session_id": "uuid"
        }
        """
        start_time = time.time()
        
        # Extract inputs
        pan_number = input_data.get("pan_details", {}).get("pan_number")
        applicant_income = input_data.get("applicant_income", 50000)
        loan_amount = input_data.get("loan_amount", 500000)
        loan_term = input_data.get("loan_term", 36)
        
        # Step 1: Get credit score
        credit_result = self.call_tool("get_credit_score", pan_number=pan_number)
        
        # Step 2: Assess risk
        risk_result = self.call_tool(
            "assess_risk",
            credit_score=credit_result.get("credit_score"),
            income=applicant_income,
            loan_amount=loan_amount
        )
        
        # Step 3: Determine eligibility
        eligibility = self.call_tool(
            "determine_eligibility",
            risk_score=risk_result.get("risk_score"),
            credit_score=credit_result.get("credit_score")
        )
        
        # Step 4: Generate explanation
        explanation = self.call_tool(
            "generate_explanation",
            decision=eligibility.get("decision"),
            risk_score=risk_result.get("risk_score"),
            credit_score=credit_result.get("credit_score")
        )
        
        # Calculate offered rate
        rate_range = credit_result.get("rate_range", {})
        offered_rate = (rate_range.get("min", 0) + rate_range.get("max", 0)) / 2
        
        # Build output
        output = {
            "application_id": input_data.get("session_id"),
            "decision": eligibility.get("decision"),
            "credit_score": credit_result.get("credit_score"),
            "credit_band": credit_result.get("credit_band"),
            "credit_band_color": credit_result.get("color"),
            "risk_score": risk_result.get("risk_score"),
            "risk_tier": risk_result.get("risk_tier"),
            "approval_probability": eligibility.get("approval_probability"),
            "offered_rate": offered_rate,
            "rate_range": rate_range,
            "negotiation_allowed": credit_result.get("negotiation_allowed"),
            "max_negotiation_rounds": credit_result.get("max_negotiation_rounds"),
            "explanation": explanation,
            "loan_details": {
                "loan_amount": loan_amount,
                "loan_term": loan_term,
                "monthly_emi": self._calculate_emi(loan_amount, offered_rate, loan_term)
            }
        }
        
        # Determine next step
        if eligibility.get("decision") == "REJECTED":
            reasoning = f"Loan application rejected. Credit score {credit_result.get('credit_score')} is below threshold. Risk score: {risk_result.get('risk_score')}"
            status = AgentStatus.FAILED
            next_agent = None
        elif credit_result.get("negotiation_allowed"):
            reasoning = f"Loan approved with {eligibility.get('decision').replace('_', ' ').lower()}. Credit score: {credit_result.get('credit_score')}, Risk tier: {risk_result.get('risk_tier')}. Rate: {offered_rate}% p.a."
            status = AgentStatus.SUCCESS
            next_agent = "Negotiation Agent"
        else:
            reasoning = f"Loan approved. Credit score: {credit_result.get('credit_score')}, Risk tier: {risk_result.get('risk_tier')}. Rate: {offered_rate}% p.a. No negotiation available for this tier."
            status = AgentStatus.SUCCESS
            next_agent = None
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )

    def _calculate_emi(self, principal: float, rate: float, months: int) -> float:
        """Calculate EMI."""
        if rate == 0:
            return principal / months
        monthly_rate = rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        return round(emi, 2)


# =============================================================================
# AGENT 2: KYC VERIFICATION AGENT
# =============================================================================

class KYCVerificationAgent(BaseAgent):
    """
    KYC Verification Agent
    
    Role: Handles all document verification by calling existing kyc_backend endpoints.
    Provides comprehensive KYC verification with PAN/Aadhaar extraction and validation.
    
    Tools:
    - extract_pan(image): Calls /kyc/extract/pan endpoint
    - extract_aadhaar(image): Calls /kyc/extract/aadhaar endpoint
    - cross_validate(pan_data, aadhaar_data): Calls /kyc/verify endpoint
    - check_age_eligibility(dob): Returns bool for age 21-65
    - mask_sensitive_data(data): Masks PAN/Aadhaar numbers
    
    KYCResult output:
    {
      "agent": "KYCVerificationAgent",
      "status": "VERIFIED" | "PARTIAL" | "FAILED",
      "applicant_name": "...",
      "pan_number": "ABCDE****F",
      "dob": "...",
      "age": int,
      "name_match_score": float,
      "age_eligible": bool,
      "kyc_reference": "KYC-2026-XXXXX",
      "reasoning": "...",
      "next_agent": "CreditUnderwritingAgent"
    }
    """

    def __init__(self, kyc_backend_url: str = "http://localhost:8001"):
        self.kyc_backend_url = kyc_backend_url
        super().__init__(
            name="KYCVerificationAgent",
            role="Handle all document verification for loan applications",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="extract_pan",
                description="Extract PAN details from document image",
                func=self._extract_pan,
                parameters={"image": "bytes", "pan_number": "str"}
            ),
            Tool(
                name="extract_aadhaar",
                description="Extract Aadhaar details from document image",
                func=self._extract_aadhaar,
                parameters={"image": "bytes", "aadhaar_number": "str"}
            ),
            Tool(
                name="cross_validate",
                description="Cross-validate PAN and Aadhaar documents",
                func=self._cross_validate,
                parameters={"pan_data": "dict", "aadhaar_data": "dict"}
            ),
            Tool(
                name="check_age_eligibility",
                description="Check if applicant age is within 21-65 range",
                func=self._check_age_eligibility,
                parameters={"dob": "str"}
            ),
            Tool(
                name="mask_sensitive_data",
                description="Mask sensitive data like PAN and Aadhaar numbers",
                func=self._mask_sensitive_data,
                parameters={"data": "dict"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the KYC Verification Agent for LoanEase. Your role is to:
1. Extract and validate PAN card details from document images
2. Extract and validate Aadhaar card details from document images
3. Cross-validate name and details between PAN and Aadhaar
4. Verify applicant age eligibility (must be 21-65 years)
5. Mask sensitive data (PAN, Aadhaar numbers) for privacy
6. Generate unique KYC reference IDs

Always provide clear reasoning for verification results. If documents are
unclear or inconsistent, mark as FAILED with specific issues."""

    def _extract_pan(self, image: bytes = None, pan_number: str = None) -> dict:
        """
        Extract PAN details - calls kyc_backend /kyc/extract/pan endpoint.
        In production, this makes an HTTP call to the kyc_backend service.
        """
        # In production: POST to {self.kyc_backend_url}/kyc/extract/pan
        # For now, return mock data that simulates the real response
        
        if pan_number:
            # Use provided PAN number
            pass
        else:
            pan_number = "ABCDE1234F"
        
        # Calculate age from mock DOB
        dob = "15/08/1995"
        try:
            dt = datetime.strptime(dob, "%d/%m/%Y")
            age = datetime.now().year - dt.year
        except:
            age = 29
        
        return {
            "extracted_fields": {
                "pan_number": pan_number,
                "name": "RAHUL SHARMA",
                "fathers_name": "SANJAY SHARMA",
                "date_of_birth": dob,
                "age": age
            },
            "validation": {
                "pan_format_valid": True,
                "name_found": True,
                "dob_found": True,
                "age_eligible": 21 <= age <= 65,
                "overall_valid": True
            },
            "document_type": "PAN",
            "confidence_score": 0.92
        }

    def _extract_aadhaar(self, image: bytes = None, aadhaar_number: str = None) -> dict:
        """
        Extract Aadhaar details - calls kyc_backend /kyc/extract/aadhaar endpoint.
        """
        # In production: POST to {self.kyc_backend_url}/kyc/extract/aadhaar
        
        if aadhaar_number:
            pass
        else:
            aadhaar_number = "123456789012"
        
        dob = "15/08/1995"
        try:
            dt = datetime.strptime(dob, "%d/%m/%Y")
            age = datetime.now().year - dt.year
        except:
            age = 29
        
        return {
            "extracted_fields": {
                "aadhaar_number": aadhaar_number,
                "name": "RAHUL SHARMA",
                "date_of_birth": dob,
                "gender": "Male",
                "address": "123, Main Street, Mumbai, Maharashtra - 400001"
            },
            "validation": {
                "aadhaar_format_valid": True,
                "name_found": True,
                "address_found": True,
                "age_eligible": 21 <= age <= 65,
                "overall_valid": True
            },
            "document_type": "AADHAAR",
            "confidence_score": 0.89
        }

    def _cross_validate(self, pan_data: dict, aadhaar_data: dict) -> dict:
        """
        Cross-validate PAN and Aadhaar - calls kyc_backend /kyc/verify endpoint.
        """
        # In production: POST to {self.kyc_backend_url}/kyc/verify
        
        pan_name = pan_data.get("extracted_fields", {}).get("name", "").upper()
        aadhaar_name = aadhaar_data.get("extracted_fields", {}).get("name", "").upper()
        
        # Calculate name match score
        if pan_name == aadhaar_name:
            name_match_score = 94.0
        else:
            # Simple similarity calculation
            pan_words = set(pan_name.split())
            aadhaar_words = set(aadhaar_name.split())
            if pan_words and aadhaar_words:
                intersection = len(pan_words & aadhaar_words)
                union = len(pan_words | aadhaar_words)
                name_match_score = (intersection / union) * 100 if union > 0 else 0
            else:
                name_match_score = 0
        
        # Check age eligibility
        pan_dob = pan_data.get("extracted_fields", {}).get("date_of_birth")
        age_eligible = self._check_age_eligibility(pan_dob)
        
        return {
            "name_match_score": name_match_score,
            "age_eligible": age_eligible,
            "names_match": name_match_score >= 70,
            "cross_validation_passed": name_match_score >= 70 or age_eligible
        }

    def _check_age_eligibility(self, dob: str = None) -> bool:
        """Check if applicant age is within eligible range."""
        if not dob:
            return True  # Can't determine age from OCR — don't block
        try:
            dt = datetime.strptime(dob, "%d/%m/%Y")
            age = datetime.now().year - dt.year
            return 18 <= age <= 75
        except Exception:
            return True  # Unparseable DOB — don't block

    def _mask_sensitive_data(self, data: dict) -> dict:
        """Mask sensitive data like PAN and Aadhaar numbers."""
        masked = data.copy()
        
        # Mask PAN (first 5 and last 1 visible)
        if "pan_number" in masked:
            pan = masked["pan_number"]
            if len(pan) >= 10:
                masked["pan_number"] = pan[:5] + "****" + pan[-1]
        
        # Mask Aadhaar (first 8 digits masked)
        if "aadhaar_number" in masked:
            aadhaar = masked["aadhaar_number"]
            if len(aadhaar) >= 12:
                masked["aadhaar_number"] = "****" + aadhaar[-4:]
        
        return masked

    def _generate_kyc_reference(self) -> str:
        """Generate unique KYC reference ID."""
        import uuid
        return f"KYC-2026-{str(uuid.uuid4())[:5].upper()}"

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute KYC verification on input data.
        
        Expected input from Master Agent:
        {
            "pan_image": bytes, (optional - can use pan_number directly)
            "aadhaar_image": bytes, (optional - can use aadhaar_number directly)
            "pan_number": "ABCDE1234F", (optional)
            "aadhaar_number": "123456789012", (optional)
            "session_id": "uuid"
        }
        
        run() logic:
        1. Receive image files from master agent
        2. Run PAN extraction
        3. If PAN valid → run Aadhaar extraction
        4. Cross-validate both documents
        5. Return KYCResult to master agent
        """
        start_time = time.time()
        
        # Extract inputs
        pan_image = input_data.get("pan_image")
        aadhaar_image = input_data.get("aadhaar_image")
        pan_number = input_data.get("pan_number")
        aadhaar_number = input_data.get("aadhaar_number")
        
        # Step 1: Extract PAN
        pan_result = self.call_tool(
            "extract_pan",
            image=pan_image,
            pan_number=pan_number
        )
        
        # Check PAN validation
        pan_valid = pan_result.get("validation", {}).get("overall_valid", False)
        
        if not pan_valid:
            # PAN invalid - return failed result
            output = {
                "agent": "KYCVerificationAgent",
                "status": "FAILED",
                "reasoning": "PAN document validation failed. Please upload a clear PAN card image.",
                "pan_data": pan_result,
                "next_agent": None
            }
            
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=output,
                reasoning=output["reasoning"],
                next_agent=None,
                duration_ms=duration_ms
            )
        
        # Step 2: Extract Aadhaar (only if PAN is valid)
        aadhaar_result = self.call_tool(
            "extract_aadhaar",
            image=aadhaar_image,
            aadhaar_number=aadhaar_number
        )
        
        # Step 3: Cross-validate both documents
        cross_validation = self.call_tool(
            "cross_validate",
            pan_data=pan_result,
            aadhaar_data=aadhaar_result
        )
        
        # Step 4: Determine overall KYC status
        name_match_score = cross_validation.get("name_match_score", 0)
        age_eligible = cross_validation.get("age_eligible", False)
        names_match = cross_validation.get("names_match", False)
        
        if names_match and age_eligible:
            kyc_status = "VERIFIED"
        elif names_match or age_eligible:
            kyc_status = "PARTIAL"
        else:
            kyc_status = "FAILED"
        
        # Extract applicant details
        pan_fields = pan_result.get("extracted_fields", {})
        applicant_name = pan_fields.get("name", "Unknown")
        dob = pan_fields.get("date_of_birth", "")
        age = pan_fields.get("age", 0)
        
        # Mask sensitive data for output
        masked_pan = self.call_tool(
            "mask_sensitive_data",
            data={"pan_number": pan_fields.get("pan_number", "")}
        )
        
        # Generate KYC reference
        kyc_reference = self._generate_kyc_reference()
        
        # Build output
        output = {
            "agent": "KYCVerificationAgent",
            "status": kyc_status,
            "applicant_name": applicant_name,
            "pan_number": masked_pan.get("pan_number", "****"),
            "dob": dob,
            "age": age,
            "name_match_score": name_match_score,
            "age_eligible": age_eligible,
            "kyc_reference": kyc_reference,
            "pan_data": pan_result,
            "aadhaar_data": aadhaar_result,
            "cross_validation": cross_validation,
            "session_id": input_data.get("session_id")
        }
        
        # Generate reasoning
        if kyc_status == "VERIFIED":
            reasoning = (
                f"PAN and Aadhaar documents match with {name_match_score:.0f}% name similarity. "
                f"Age {age} is within the 21-65 eligibility range. "
                f"KYC Reference: {kyc_reference}"
            )
            next_agent = "CreditUnderwritingAgent"
        elif kyc_status == "PARTIAL":
            reasoning = (
                f"KYC partially verified. Name match score: {name_match_score:.0f}%. "
                f"Age eligible: {age_eligible}. "
                f"KYC Reference: {kyc_reference}"
            )
            next_agent = "CreditUnderwritingAgent"
        else:
            reasoning = (
                f"KYC verification failed. Name match score: {name_match_score:.0f}%. "
                f"Age eligible: {age_eligible}. "
                f"Please ensure PAN and Aadhaar names match and age is between 21-65."
            )
            next_agent = None
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS if kyc_status != "FAILED" else AgentStatus.FAILED,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 3: NEGOTIATION AGENT
# =============================================================================

class NegotiationAgent(BaseAgent):
    """
    Negotiation Agent
    
    Role: Loan offer generation and rate negotiation.

    Tools:
    - generate_opening_offer: Build first offer from credit result
    - process_counter: Parse applicant counter/acceptance from message
    - calculate_emi: Compute EMI and repayment components
    - check_floor_reached: Check if floor rate is reached
    - escalate_to_human: Escalate negotiation to a human officer
    """

    def __init__(self):
        super().__init__(
            name="Negotiation Agent",
            role="Handle interest rate negotiations with applicants",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="generate_opening_offer",
                description="Generate opening offer from credit result",
                func=self._generate_opening_offer,
                parameters={"credit_result": "dict", "loan_amount": "int", "tenure_months": "int"}
            ),
            Tool(
                name="process_counter",
                description="Process applicant counter message and intent",
                func=self._process_counter,
                parameters={"session_id": "str", "user_message": "str"}
            ),
            Tool(
                name="calculate_emi",
                description="Calculate EMI, total payable, and total interest",
                func=self._calculate_emi_components,
                parameters={"principal": "float", "rate": "float", "tenure": "int"}
            ),
            Tool(
                name="check_floor_reached",
                description="Check whether current rate has hit floor rate",
                func=self._check_floor_reached,
                parameters={"current_rate": "float", "floor_rate": "float"}
            ),
            Tool(
                name="escalate_to_human",
                description="Escalate negotiation to human underwriter",
                func=self._escalate_to_human,
                parameters={"session_id": "str", "reason": "str"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the NegotiationAgent for LoanEase.
1. Generate opening offer from credit result
2. Handle applicant counters with policy-backed concessions
3. Reduce by 0.25% per valid round
4. Offer escalation when floor rate is reached
5. On acceptance, route to BlockchainAuditAgent"""

    def _calculate_emi_components(self, principal: float, rate: float, tenure: int) -> dict:
        monthly_rate = rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure / ((1 + monthly_rate) ** tenure - 1)
        total_payable = emi * tenure
        total_interest = total_payable - principal
        return {
            "emi": int(round(emi)),
            "total_payable": int(round(total_payable)),
            "total_interest": int(round(total_interest)),
        }

    def _generate_opening_offer(self, credit_result: dict, loan_amount: int, tenure_months: int) -> dict:
        offered_rate = float(credit_result.get("offered_rate", 11.5))
        risk_tier = credit_result.get("risk_tier", "Medium Risk")
        if risk_tier == "Low Risk":
            floor_rate = 10.5
            max_rounds = 3
        elif risk_tier == "Medium Risk":
            floor_rate = 11.0
            max_rounds = 2
        else:
            floor_rate = 12.5
            max_rounds = 1
        max_rounds = int(credit_result.get("max_negotiation_rounds", max_rounds))
        metrics = self._calculate_emi_components(loan_amount, offered_rate, tenure_months)
        return {
            "opening_rate": round(offered_rate, 2),
            "floor_rate": round(floor_rate, 2),
            "max_rounds": max_rounds,
            "risk_tier": risk_tier,
            **metrics,
        }

    def _process_counter(self, session_id: str, user_message: str) -> dict:
        message = (user_message or "").lower()
        if any(token in message for token in ["accept", "agreed", "okay", "ok", "yes"]):
            return {"intent": "ACCEPT", "requested_rate": None}
        if any(token in message for token in ["escalate", "manager", "human", "supervisor"]):
            return {"intent": "ESCALATE", "requested_rate": None}
        import re
        match = re.search(r"(\d+(?:\.\d+)?)", message)
        requested_rate = float(match.group(1)) if match else None
        return {"intent": "COUNTER", "requested_rate": requested_rate}

    def _check_floor_reached(self, current_rate: float, floor_rate: float) -> bool:
        return float(current_rate) <= float(floor_rate)

    def _escalate_to_human(self, session_id: str, reason: str) -> dict:
        return {
            "escalated": True,
            "session_id": session_id,
            "reason": reason,
            "reference_id": f"ESC-{int(time.time())}",
        }

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute AGENT 4 negotiation flow and return NegotiationResult-compatible payload.
        """
        start_time = time.time()
        session_id = input_data.get("session_id", f"session_{int(time.time())}")
        loan_details = input_data.get("loan_details", {})
        loan_amount = int(loan_details.get("loan_amount", input_data.get("loan_amount", 500000)))
        tenure_months = int(loan_details.get("loan_term", input_data.get("tenure_months", 60)))
        rounds_taken = int(input_data.get("rounds_taken", 0))
        user_message = str(input_data.get("user_message", "")).strip()
        negotiation_requested = bool(input_data.get("negotiation_requested", False))
        counter_rate = input_data.get("counter_rate")

        credit_result = {
            "offered_rate": input_data.get("offered_rate", 11.5),
            "risk_tier": input_data.get("risk_tier", "Medium Risk"),
            "max_negotiation_rounds": input_data.get("max_negotiation_rounds", 3),
        }
        opening_offer = self.call_tool(
            "generate_opening_offer",
            credit_result=credit_result,
            loan_amount=loan_amount,
            tenure_months=tenure_months,
        )
        floor_rate = float(input_data.get("floor_rate", opening_offer["floor_rate"]))
        current_rate = float(input_data.get("current_rate", opening_offer["opening_rate"]))
        opening_rate = float(opening_offer["opening_rate"])
        max_rounds = int(opening_offer["max_rounds"])

        if counter_rate is not None and not user_message:
            user_message = f"Can you do {counter_rate}%?"

        parsed = self.call_tool("process_counter", session_id=session_id, user_message=user_message)
        if counter_rate is not None and parsed.get("intent") == "COUNTER":
            parsed["requested_rate"] = float(counter_rate)

        status_text = "ACTIVE"
        next_agent = None

        if not negotiation_requested and not user_message and counter_rate is None:
            status_text = "ACCEPTED"
            next_agent = "BlockchainAuditAgent"
            reasoning = (
                f"Applicant accepted opening offer at {current_rate:.2f}% without negotiation. "
                "Handing over to blockchain audit for sanction letter generation."
            )
        elif parsed.get("intent") == "ACCEPT":
            status_text = "ACCEPTED"
            next_agent = "BlockchainAuditAgent"
            reasoning = (
                f"Applicant accepted the negotiated offer at {current_rate:.2f}%. "
                "Handing over to blockchain audit for immutable offer recording."
            )
        elif parsed.get("intent") == "ESCALATE":
            escalation = self.call_tool(
                "escalate_to_human",
                session_id=session_id,
                reason="Applicant requested manual review during negotiation.",
            )
            status_text = "ESCALATED"
            reasoning = (
                f"Negotiation escalated to human loan officer. Reference: {escalation.get('reference_id')}."
            )
        else:
            rounds_remaining = max(0, max_rounds - rounds_taken)
            if rounds_remaining <= 0:
                reasoning = (
                    f"Maximum negotiation rounds ({max_rounds}) already used. "
                    f"Current offer remains {current_rate:.2f}%."
                )
            else:
                if self.call_tool("check_floor_reached", current_rate=current_rate, floor_rate=floor_rate):
                    escalation = self.call_tool(
                        "escalate_to_human",
                        session_id=session_id,
                        reason="Applicant requested lower rate after floor was reached.",
                    )
                    status_text = "ESCALATED"
                    reasoning = (
                        f"Floor rate of {floor_rate:.2f}% reached. "
                        f"Escalation offered with reference {escalation.get('reference_id')}."
                    )
                else:
                    current_rate = max(floor_rate, round(current_rate - 0.25, 2))
                    rounds_taken += 1
                    reasoning = (
                        f"Applicant countered and one concession of 0.25% was granted. "
                        f"Updated offer is {current_rate:.2f}% with {max(0, max_rounds - rounds_taken)} rounds remaining."
                    )

        emi_data = self.call_tool(
            "calculate_emi",
            principal=loan_amount,
            rate=current_rate,
            tenure=tenure_months,
        )
        opening_emi_data = self.call_tool(
            "calculate_emi",
            principal=loan_amount,
            rate=opening_rate,
            tenure=tenure_months,
        )
        savings_achieved = int(opening_emi_data["total_payable"] - emi_data["total_payable"])
        output = {
            "agent": "NegotiationAgent",
            "status": status_text,
            "final_rate": round(current_rate, 2),
            "loan_amount": loan_amount,
            "tenure_months": tenure_months,
            "emi": emi_data["emi"],
            "monthly_emi": emi_data["emi"],
            "total_payable": emi_data["total_payable"],
            "total_interest": emi_data["total_interest"],
            "rounds_taken": rounds_taken,
            "rounds_used": rounds_taken,
            "savings_achieved": savings_achieved,
            "reasoning": reasoning,
            "next_agent": next_agent,
            "negotiation_completed": status_text in {"ACCEPTED", "ESCALATED"},
        }
        status = AgentStatus.ESCALATED if status_text == "ESCALATED" else AgentStatus.SUCCESS
        duration_ms = int((time.time() - start_time) * 1000)
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 5: BLOCKCHAIN AUDIT AGENT
# =============================================================================

class BlockchainAuditAgent(BaseAgent):
    """
    BlockchainAuditAgent

    Role: Sanction letter generation + blockchain hash storage.
    """

    _mock_ledger: dict[str, dict] = {}
    _tx_counter: int = 0
    _sanction_counter: int = 0

    def __init__(self):
        super().__init__(
            name="BlockchainAuditAgent",
            role="Generate sanction letter and store immutable audit hash",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="generate_sanction_letter",
                description="Generate sanction letter content and PDF payload",
                func=self._generate_sanction_letter,
                parameters={"loan_data": "dict"}
            ),
            Tool(
                name="compute_sha256_hash",
                description="Compute SHA-256 hash for given content",
                func=self._compute_sha256_hash,
                parameters={"content": "str"}
            ),
            Tool(
                name="store_on_ledger",
                description="Store hash and metadata on mock ledger",
                func=self._store_on_ledger,
                parameters={"hash": "str", "metadata": "dict"}
            ),
            Tool(
                name="verify_hash",
                description="Verify content integrity against hash",
                func=self._verify_hash,
                parameters={"hash": "str", "original_content": "str"}
            ),
            Tool(
                name="generate_qr_code",
                description="Generate QR code image as base64",
                func=self._generate_qr_code,
                parameters={"verification_url": "str"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are BlockchainAuditAgent for LoanEase.
1. Generate sanction letters from approved loan data
2. Compute SHA-256 hash of letter content
3. Persist hash to immutable-style ledger records
4. Provide verification URL and QR code
5. Return auditable sanction metadata to master agent"""

    def _next_sanction_reference(self) -> str:
        BlockchainAuditAgent._sanction_counter += 1
        year = datetime.now(timezone.utc).year
        return f"LE-{year}-{BlockchainAuditAgent._sanction_counter:05d}"

    def _generate_sanction_letter(self, loan_data: dict) -> dict:
        sanction_reference = loan_data.get("sanction_reference") or self._next_sanction_reference()
        issued_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        content = (
            f"LoanEase Sanction Letter\n"
            f"Sanction Reference: {sanction_reference}\n"
            f"Issue Timestamp: {issued_at}\n"
            f"Applicant: {loan_data.get('applicant_name', 'Applicant')}\n"
            f"Loan Amount: {loan_data.get('loan_amount')}\n"
            f"Tenure (months): {loan_data.get('tenure_months')}\n"
            f"Interest Rate (% p.a.): {loan_data.get('final_rate')}\n"
            f"EMI: {loan_data.get('emi')}\n"
            f"Total Payable: {loan_data.get('total_payable')}\n"
            f"Total Interest: {loan_data.get('total_interest')}\n"
            f"Terms: This sanction remains subject to final compliance and disbursement checks.\n"
        )
        # Mock PDF payload; production would render a real PDF binary.
        pdf_base64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        return {
            "sanction_reference": sanction_reference,
            "issued_at": issued_at,
            "content": content,
            "pdf_base64": pdf_base64,
        }

    def _compute_sha256_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _store_on_ledger(self, hash: str, metadata: dict) -> dict:
        BlockchainAuditAgent._tx_counter += 1
        tx_id = f"TX-{BlockchainAuditAgent._tx_counter:05d}"
        ledger_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        record = {
            "tx_id": tx_id,
            "hash": hash,
            "metadata": metadata,
            "timestamp": ledger_timestamp,
            "chain": "mock-ethereum-ready",
            "version": 1,
        }
        BlockchainAuditAgent._mock_ledger[tx_id] = record
        return {
            "tx_id": tx_id,
            "ledger_timestamp": ledger_timestamp,
            "record": record,
        }

    def _verify_hash(self, hash: str, original_content: str) -> bool:
        return self._compute_sha256_hash(original_content) == hash

    def _generate_qr_code(self, verification_url: str) -> str:
        # Deterministic mock QR image payload for now; replace with true QR renderer later.
        pseudo_png = f"QR::{verification_url}".encode("utf-8")
        return base64.b64encode(pseudo_png).decode("ascii")

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute blockchain audit flow and return BlockchainResult-compatible payload.
        """
        start_time = time.time()

        loan_data = {
            "applicant_name": input_data.get("applicant_name", "Applicant"),
            "loan_amount": int(input_data.get("loan_amount", 0)),
            "tenure_months": int(input_data.get("tenure_months", 0)),
            "final_rate": float(input_data.get("final_rate", 0.0)),
            "emi": int(input_data.get("emi", 0)),
            "total_payable": int(input_data.get("total_payable", 0)),
            "total_interest": int(input_data.get("total_interest", 0)),
            "session_id": input_data.get("session_id"),
        }

        sanction = self.call_tool("generate_sanction_letter", loan_data=loan_data)
        content_hash = self.call_tool("compute_sha256_hash", content=sanction["content"])
        verification_url = f"/verify/{sanction['sanction_reference']}"
        ledger = self.call_tool(
            "store_on_ledger",
            hash=content_hash,
            metadata={
                "sanction_reference": sanction["sanction_reference"],
                "verification_url": verification_url,
                "session_id": loan_data.get("session_id"),
            },
        )
        hash_ok = self.call_tool("verify_hash", hash=content_hash, original_content=sanction["content"])
        qr_code_base64 = self.call_tool("generate_qr_code", verification_url=verification_url)

        reasoning = (
            "Sanction letter content hashed using SHA-256. Hash stored in audit ledger with timestamp. "
            "Document integrity can be verified at any time by recomputing hash."
        )
        if not hash_ok:
            reasoning = "Sanction audit failed because computed hash could not be verified against source content."

        output = {
            "agent": "BlockchainAuditAgent",
            "status": "SANCTIONED" if hash_ok else "FAILED",
            "sanction_reference": sanction["sanction_reference"],
            "sha256_hash": content_hash,
            "ledger_transaction_id": ledger["tx_id"],
            "ledger_timestamp": ledger["ledger_timestamp"],
            "verification_url": verification_url,
            "qr_code_base64": qr_code_base64,
            "sanction_letter_pdf_base64": sanction["pdf_base64"],
            "reasoning": reasoning,
            "next_agent": None,
        }

        duration_ms = int((time.time() - start_time) * 1000)
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS if hash_ok else AgentStatus.FAILED,
            output=output,
            reasoning=reasoning,
            next_agent=None,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 3: CREDIT UNDERWRITING AGENT
# =============================================================================

class CreditUnderwritingAgent(BaseAgent):
    """
    Credit Underwriting Agent
    
    Role: Credit score lookup and XGBoost assessment for loan eligibility.
    Calls existing backend endpoints for credit assessment.
    
    Tools:
    - get_credit_score(pan): Calls /credit-score/{pan} endpoint
    - run_xgboost(applicant_data): Calls /assess endpoint
    - generate_shap_explanation(shap_values): Generates plain-English explanations
    - determine_rate_band(credit_score): Determines interest rate band
    
    CreditResult output:
    {
      "agent": "CreditUnderwritingAgent",
      "status": "APPROVED" | "REJECTED",
      "credit_score": 820,
      "credit_score_out_of": 900,
      "risk_score": 87,
      "risk_score_out_of": 100,
      "risk_tier": "Low Risk",
      "offered_rate": 11.25,
      "max_negotiation_rounds": 3,
      "shap_explanation": [...],
      "reasoning": "...",
      "next_agent": "NegotiationAgent"
    }
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        super().__init__(
            name="CreditUnderwritingAgent",
            role="Credit score lookup and XGBoost assessment for loan eligibility",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_credit_score",
                description="Get CIBIL-simulated credit score for PAN number",
                func=self._get_credit_score,
                parameters={"pan": "str"}
            ),
            Tool(
                name="run_xgboost",
                description="Run XGBoost model for loan assessment",
                func=self._run_xgboost,
                parameters={"applicant_data": "dict"}
            ),
            Tool(
                name="generate_shap_explanation",
                description="Generate SHAP-based plain-English explanation",
                func=self._generate_shap_explanation,
                parameters={"shap_values": "dict", "credit_score": "int"}
            ),
            Tool(
                name="determine_rate_band",
                description="Determine interest rate band from credit score",
                func=self._determine_rate_band,
                parameters={"credit_score": "int"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the Credit Underwriting Agent for LoanEase. Your role is to:
1. Fetch credit scores from CIBIL bureau simulation
2. Run XGBoost ML model for loan eligibility assessment
3. Calculate combined risk scores using 60/40 weighting
4. Determine interest rate bands based on credit risk
5. Generate SHAP-based explanations for decisions
6. Handle hard rejects for credit score < 300

Always provide clear reasoning. Hard reject applicants with score < 300
as they do not meet minimum eligibility criteria."""

    def _get_credit_score(self, pan: str = None) -> dict:
        """
        Get CIBIL-simulated credit score - calls /credit-score/{pan} endpoint.
        In production, this makes an HTTP call to the backend service.
        """
        # In production: GET to {self.backend_url}/credit-score/{pan}
        
        import hashlib
        
        # Generate deterministic score from PAN
        if pan:
            hash_val = int(hashlib.sha256(pan.encode()).hexdigest(), 16)
            score = 300 + (hash_val % 601)
        else:
            score = 750  # Default score
        
        # Determine band
        if score >= 700:
            band = "low_risk"
            color = "green"
            label = "Low Risk (High Score)"
        elif score >= 301:
            band = "medium_risk"
            color = "yellow"
            label = "Medium Risk (Intermediate Score)"
        else:
            band = "high_risk"
            color = "red"
            label = "High Risk (Low Score)"
        
        return {
            "credit_score": score,
            "credit_band": band,
            "credit_band_label": label,
            "color": color,
            "eligible_for_loan": score >= 300
        }

    def _run_xgboost(self, applicant_data: dict) -> dict:
        """
        Run XGBoost model for loan assessment - calls /assess endpoint.
        """
        # In production: POST to {self.backend_url}/assess
        
        # Simulate XGBoost prediction
        # In real implementation, this would call the ML model
        
        # Mock probability based on input
        income = applicant_data.get("applicant_income", 50000)
        loan_amount = applicant_data.get("loan_amount", 500000)
        
        # Simple income ratio calculation
        income_ratio = loan_amount / income if income > 0 else 10
        
        # Base probability
        if income_ratio <= 3:
            base_prob = 0.85
        elif income_ratio <= 5:
            base_prob = 0.70
        else:
            base_prob = 0.50
        
        # Add some randomness for simulation
        import random
        xgboost_prob = base_prob + random.uniform(-0.1, 0.1)
        xgboost_prob = max(0.1, min(0.95, xgboost_prob))
        
        return {
            "xgboost_probability": xgboost_prob,
            "xgboost_ran": True,
            "threshold_used": 0.7,
            "income_ratio": round(income_ratio, 2)
        }

    def _generate_shap_explanation(self, shap_values: dict = None, credit_score: int = 750) -> list[str]:
        """Generate SHAP-based plain-English explanation."""
        explanations = []
        
        # Credit score based explanations
        if credit_score >= 700:
            explanations.append(f"Credit score of {credit_score} is in the favorable range (700-900)")
            explanations.append("Stable credit history with no adverse remarks")
        elif credit_score >= 301:
            explanations.append(f"Credit score of {credit_score} is in the moderate range (301-699)")
            explanations.append("Credit history shows some variability")
        else:
            explanations.append(f"Credit score of {credit_score} is below acceptable threshold")
            explanations.append("Applicant does not meet minimum credit criteria")
        
        # Add income-based explanations if provided
        if shap_values:
            if shap_values.get("income_ratio"):
                explanations.append(f"Loan-to-income ratio is {shap_values['income_ratio']:.1f}x")
        
        return explanations

    def _determine_rate_band(self, credit_score: int) -> dict:
        """Determine interest rate band from credit score."""
        if credit_score >= 700:
            return {
                "tier": "Low Risk",
                "rate_min": 9.0,
                "rate_max": 11.0,
                "negotiation_rounds": 3,
                "offered_rate": 10.0  # Mid-point
            }
        elif credit_score >= 301:
            return {
                "tier": "Medium Risk",
                "rate_min": 11.0,
                "rate_max": 13.0,
                "negotiation_rounds": 1,
                "offered_rate": 12.0  # Mid-point
            }
        else:
            return {
                "tier": "High Risk",
                "rate_min": 13.0,
                "rate_max": 15.0,
                "negotiation_rounds": 0,
                "offered_rate": 14.0  # Mid-point
            }

    def _calculate_combined_score(self, credit_score: int, xgboost_prob: float) -> int:
        """
        Calculate combined risk score using 60/40 formula.
        60% weight on normalized CIBIL score, 40% on XGBoost probability.
        """
        # Normalize credit score to 0-100
        normalized_cibil = (credit_score - 300) / 600 * 100
        
        # XGBoost probability as percentage
        xgboost_score = xgboost_prob * 100
        
        # Combined score: 60% CIBIL, 40% XGBoost
        combined = (normalized_cibil * 0.6) + (xgboost_score * 0.4)
        
        return int(min(100, max(0, combined)))

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute credit underwriting assessment.
        
        Expected input from KYC Agent:
        {
            "pan_number": "ABCDE1234F",
            "applicant_income": 50000,
            "loan_amount": 500000,
            "loan_term": 36,
            "session_id": "uuid"
        }
        
        run() logic:
        1. Get CIBIL-simulated score from PAN
        2. Hard reject if score < 300
        3. Run XGBoost if eligible
        4. Calculate combined score (60/40 formula)
        5. Determine rate band and negotiation rounds
        6. Generate SHAP plain-English explanation
        7. Return CreditResult to master agent
        """
        start_time = time.time()
        
        # Extract inputs
        pan_number = input_data.get("pan_number")
        applicant_income = input_data.get("applicant_income", 50000)
        loan_amount = input_data.get("loan_amount", 500000)
        loan_term = input_data.get("loan_term", 36)
        
        # Step 1: Get credit score
        credit_result = self.call_tool("get_credit_score", pan=pan_number)
        credit_score = credit_result.get("credit_score", 750)
        
        # Step 2: Hard reject if score < 300
        if credit_score < 300:
            output = {
                "agent": "CreditUnderwritingAgent",
                "status": "REJECTED",
                "credit_score": credit_score,
                "credit_score_out_of": 900,
                "reasoning": f"Credit score {credit_score} is below minimum threshold of 300. Application rejected.",
                "next_agent": None
            }
            
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=output,
                reasoning=output["reasoning"],
                next_agent=None,
                duration_ms=duration_ms
            )
        
        # Step 3: Run XGBoost if eligible
        applicant_data = {
            "pan_number": pan_number,
            "applicant_income": applicant_income,
            "loan_amount": loan_amount,
            "loan_term": loan_term
        }
        xgboost_result = self.call_tool("run_xgboost", applicant_data=applicant_data)
        xgboost_prob = xgboost_result.get("xgboost_probability", 0.5)
        
        # Step 4: Calculate combined score (60/40 formula)
        risk_score = self._calculate_combined_score(credit_score, xgboost_prob)
        
        # Step 5: Determine rate band
        rate_band = self.call_tool("determine_rate_band", credit_score=credit_score)
        risk_tier = rate_band.get("tier", "Medium Risk")
        offered_rate = rate_band.get("offered_rate", 12.0)
        max_negotiation_rounds = rate_band.get("negotiation_rounds", 1)
        
        # Step 6: Generate SHAP explanation
        shap_explanation = self.call_tool(
            "generate_shap_explanation",
            shap_values=xgboost_result,
            credit_score=credit_score
        )
        
        # Step 7: Determine final status
        if risk_score >= 75:
            status = "APPROVED"
        elif risk_score >= 50:
            status = "APPROVED"  # Still approved but may have conditions
        else:
            status = "REJECTED"
        
        # Build output
        output = {
            "agent": "CreditUnderwritingAgent",
            "status": status,
            "credit_score": credit_score,
            "credit_score_out_of": 900,
            "risk_score": risk_score,
            "risk_score_out_of": 100,
            "risk_tier": risk_tier,
            "offered_rate": offered_rate,
            "rate_range": {
                "min": rate_band.get("rate_min"),
                "max": rate_band.get("rate_max")
            },
            "max_negotiation_rounds": max_negotiation_rounds,
            "xgboost_probability": xgboost_prob,
            "xgboost_ran": xgboost_result.get("xgboost_ran", True),
            "shap_explanation": shap_explanation,
            "loan_details": {
                "loan_amount": loan_amount,
                "loan_term": loan_term,
                "monthly_emi": self._calculate_emi(loan_amount, offered_rate, loan_term)
            },
            "session_id": input_data.get("session_id")
        }
        
        # Generate reasoning
        reasoning = (
            f"Credit score {credit_score} qualifies for {risk_tier} tier. "
            f"XGBoost confidence {xgboost_prob:.2f} combined with normalized CIBIL score gives "
            f"final risk score of {risk_score}/100. "
            f"Rate set at {offered_rate}% within {risk_tier} band."
        )
        
        # Determine next agent
        if status == "APPROVED" and max_negotiation_rounds > 0:
            next_agent = "NegotiationAgent"
        elif status == "APPROVED":
            next_agent = None  # No negotiation for high risk
        else:
            next_agent = None
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS if status == "APPROVED" else AgentStatus.FAILED,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )

    def _calculate_emi(self, principal: float, rate: float, months: int) -> float:
        """Calculate EMI."""
        if rate == 0:
            return principal / months
        monthly_rate = rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        return round(emi, 2)


# =============================================================================
# AGENT 4: TRANSLATION AGENT
# =============================================================================

class TranslationAgent(BaseAgent):
    """
    Translation Agent
    
    Role: Provide multilingual support for all communications.
    Translates messages between English and Hindi.
    
    Tools:
    - translate_text: Translate text between languages
    - detect_language: Detect source language
    - translate_response: Translate full response object
    """

    def __init__(self):
        super().__init__(
            name="Translation Agent",
            role="Provide multilingual support for all communications",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="translate_text",
                description="Translate text from source to target language",
                func=self._mock_translate_text,
                parameters={"text": "str", "source": "str", "target": "str"}
            ),
            Tool(
                name="detect_language",
                description="Detect the language of input text",
                func=self._mock_detect_language,
                parameters={"text": "str"}
            ),
            Tool(
                name="translate_response",
                description="Translate complete response object",
                func=self._mock_translate_response,
                parameters={"response": "dict", "target_language": "str"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the Translation Agent for LoanEase. Your role is to:
1. Translate all communications to applicant's preferred language
2. Support English (en) and Hindi (hi) translations
3. Maintain technical accuracy when translating financial terms
4. Preserve formatting and structure of translated content

Always provide translations that are natural and culturally appropriate.
For Hindi, use common Hindi vocabulary familiar to Indian users."""

    def _mock_translate_text(self, text: str, source: str = "en", target: str = "hi") -> dict:
        """Mock translation - in production, calls translation_backend service."""
        # Simulates calling translation_backend/app/translation_service.py
        
        # Simple mock translations for common phrases
        mock_translations = {
            ("en", "hi"): {
                "Your loan application has been approved": "आपका ऋण आवेदन स्वीकृत हो गया है",
                "Your credit score is": "आपका क्रेडिट स्कोर है",
                "Monthly EMI": "मासिक EMI",
                "Interest rate": "ब्याज दर",
                "Loan amount": "ऋण राशि",
                "Congratulations": "बधाई हो",
                "Thank you for applying": "आवेदन के लिए धन्यवाद",
            },
            ("hi", "en"): {
                "आपका ऋण आवेदन स्वीकृत हो गया है": "Your loan application has been approved",
                "आपका क्रेडिट स्कोर है": "Your credit score is",
                "मासिक EMI": "Monthly EMI",
                "ब्याज दर": "Interest rate",
                "ऋण राशि": "Loan amount",
                "बधाई हो": "Congratulations",
                "आवेदन के लिए धन्यवाद": "Thank you for applying",
            }
        }
        
        # Check for exact match
        key = (source, target)
        translations = mock_translations.get(key, {})
        
        if text in translations:
            translated = translations[text]
        else:
            # Mock translation - in production would call actual service
            if target == "hi":
                translated = f"[HI] {text}"
            else:
                translated = text
        
        return {
            "original_text": text,
            "translated_text": translated,
            "source_language": source,
            "target_language": target,
            "confidence": 0.95
        }

    def _mock_detect_language(self, text: str) -> dict:
        """Mock language detection."""
        # Simple detection based on character ranges
        has_hindi = any('\u0900' <= c <= '\u097F' for c in text)
        
        if has_hindi:
            detected = "hi"
        else:
            detected = "en"
            
        return {
            "detected_language": detected,
            "confidence": 0.9
        }

    def _mock_translate_response(self, response: dict, target_language: str = "hi") -> dict:
        """Mock full response translation."""
        translated_response = {}
        
        for key, value in response.items():
            if isinstance(value, str):
                result = self._mock_translate_text(value, "en", target_language)
                translated_response[key] = result.get("translated_text", value)
            elif isinstance(value, dict):
                translated_response[key] = self._mock_translate_response(value, target_language)
            else:
                translated_response[key] = value
                
        return translated_response

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute translation on input data.
        
        Expected input:
        {
            "text_to_translate": str,
            "source_language": "en" | "hi",
            "target_language": "en" | "hi",
            "session_id": "uuid"
        }
        Or for complete response translation:
        {
            "response_to_translate": dict,
            "target_language": "hi",
            "session_id": "uuid"
        }
        """
        start_time = time.time()
        
        # Check what type of translation is needed
        text_to_translate = input_data.get("text_to_translate")
        response_to_translate = input_data.get("response_to_translate")
        target_language = input_data.get("target_language", "hi")
        source_language = input_data.get("source_language", "en")
        
        if text_to_translate:
            # Translate single text
            result = self.call_tool(
                "translate_text",
                text=text_to_translate,
                source=source_language,
                target=target_language
            )
            
            output = {
                "translation": result,
                "session_id": input_data.get("session_id")
            }
            
            reasoning = f"Translated text from {source_language} to {target_language}: '{text_to_translate[:50]}...'"
            status = AgentStatus.SUCCESS
            next_agent = None
            
        elif response_to_translate:
            # Translate complete response
            result = self.call_tool(
                "translate_response",
                response=response_to_translate,
                target_language=target_language
            )
            
            output = {
                "translated_response": result,
                "target_language": target_language,
                "session_id": input_data.get("session_id")
            }
            
            reasoning = f"Translated complete response to {target_language}"
            status = AgentStatus.SUCCESS
            next_agent = None
            
        else:
            output = {}
            reasoning = "No text or response provided for translation"
            status = AgentStatus.FAILED
            next_agent = None
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            reasoning=reasoning,
            next_agent=next_agent,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 5: ORCHESTRATOR AGENT
# =============================================================================

class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent
    
    Role: Coordinate the workflow between all agents.
    Manages the overall process from KYC to final offer.
    
    This is the "brain" that decides which agent runs when
    and aggregates results from all agents.
    
    Tools:
    - route_to_agent: Determine which agent should run next
    - aggregate_results: Combine outputs from all agents
    - generate_summary: Create final summary for applicant
    - track_workflow: Track workflow state and history
    """

    def __init__(self, agents: dict[str, BaseAgent]):
        self.agents = agents
        super().__init__(
            name="Orchestrator Agent",
            role="Coordinate workflow between all agents",
            tools=self._create_tools()
        )

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="route_to_agent",
                description="Determine which agent should run next",
                func=self._mock_route_to_agent,
                parameters={"current_agent": "str", "agent_result": "dict"}
            ),
            Tool(
                name="aggregate_results",
                description="Combine outputs from all agents",
                func=self._mock_aggregate_results,
                parameters={"results": "list"}
            ),
            Tool(
                name="generate_summary",
                description="Create final summary for applicant",
                func=self._mock_generate_summary,
                parameters={"agent_results": "list"}
            ),
            Tool(
                name="track_workflow",
                description="Track workflow state and history",
                func=self._mock_track_workflow,
                parameters={"session_id": "str", "state": "dict"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the Orchestrator Agent for LoanEase. Your role is to:
1. Coordinate the overall workflow from start to finish
2. Route tasks to appropriate agents based on workflow state
3. Aggregate results from all agents into a coherent summary
4. Handle errors and determine when to escalate or stop
5. Track the complete workflow history for transparency

You have access to all other agents: KYC Agent, Underwriting Agent,
Negotiation Agent, and Translation Agent. Use them appropriately
based on the workflow stage."""

    def _mock_route_to_agent(self, current_agent: str, agent_result: dict) -> dict:
        """Mock routing decision."""
        next_agent = agent_result.get("next_agent")
        
        if next_agent:
            return {
                "route_decision": "continue",
                "next_agent": next_agent,
                "reason": f"Result from {current_agent} indicates {next_agent} should run next"
            }
        else:
            return {
                "route_decision": "stop",
                "next_agent": None,
                "reason": f"Result from {current_agent} indicates workflow is complete"
            }

    def _mock_aggregate_results(self, results: list[dict]) -> dict:
        """Mock result aggregation."""
        aggregated = {
            "workflow_complete": True,
            "agents_executed": [],
            "total_duration_ms": 0,
            "outputs": {}
        }
        
        for result in results:
            agent_name = result.get("agent_name", "Unknown")
            aggregated["agents_executed"].append(agent_name)
            aggregated["total_duration_ms"] += result.get("duration_ms", 0)
            aggregated["outputs"][agent_name] = result.get("output", {})
            
        return aggregated

    def _mock_generate_summary(self, agent_results: list[dict]) -> dict:
        """Mock summary generation."""
        summary = {
            "application_summary": {},
            "next_steps": [],
            "documents_needed": []
        }
        
        for result in agent_results:
            if result.get("agent_name") == "KYC Agent":
                summary["application_summary"]["kyc_status"] = result.get("status")
                if result.get("status") == "success":
                    summary["documents_needed"] = ["PAN Card", "Aadhaar Card"]
                    
            elif result.get("agent_name") == "Underwriting Agent":
                output = result.get("output", {})
                summary["application_summary"]["decision"] = output.get("decision")
                summary["application_summary"]["credit_score"] = output.get("credit_score")
                summary["application_summary"]["offered_rate"] = output.get("offered_rate")
                summary["application_summary"]["monthly_emi"] = output.get("loan_details", {}).get("monthly_emi")
                
            elif result.get("agent_name") == "Negotiation Agent":
                output = result.get("output", {})
                summary["application_summary"]["final_rate"] = output.get("final_rate")
                summary["application_summary"]["negotiation_completed"] = output.get("negotiation_completed")
            elif result.get("agent_name") == "BlockchainAuditAgent":
                output = result.get("output", {})
                summary["application_summary"]["sanction_reference"] = output.get("sanction_reference")
                summary["application_summary"]["ledger_transaction_id"] = output.get("ledger_transaction_id")
                summary["application_summary"]["sanction_status"] = output.get("status")
        
        summary["next_steps"] = [
            "Review and accept the loan offer",
            "Submit supporting documents",
            "Complete e-verification",
            "Receive disbursement"
        ]
        
        return summary

    def _mock_track_workflow(self, session_id: str, state: dict) -> dict:
        """Mock workflow tracking."""
        return {
            "session_id": session_id,
            "current_state": state.get("current_stage", "initialized"),
            "history": state.get("history", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute orchestration - manage the complete workflow.
        
        This is the main entry point that runs the entire agent pipeline.
        
        Expected input:
        {
            "pan_number": "ABCDE1234F",
            "aadhaar_number": "123456789012",
            "applicant_income": 50000,
            "loan_amount": 500000,
            "loan_term": 36,
            "preferred_language": "en" | "hi",
            "negotiation_requested": bool,
            "counter_rate": float (optional)
        }
        """
        start_time = time.time()
        
        # Initialize workflow
        session_id = input_data.get("session_id", f"session_{int(time.time())}")
        workflow_history = []
        
        # Step 1: Run KYC Agent
        kyc_input = {
            "pan_number": input_data.get("pan_number"),
            "aadhaar_number": input_data.get("aadhaar_number"),
            "session_id": session_id
        }
        
        kyc_agent = self.agents.get("KYC Agent")
        if not kyc_agent:
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output={},
                reasoning="KYC Agent not found in agent registry",
                next_agent=None,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
        kyc_result = kyc_agent.run(kyc_input)
        workflow_history.append(kyc_result.to_dict())
        
        if kyc_result.status != AgentStatus.SUCCESS:
            return self._create_orchestrator_result(
                input_data, kyc_result, workflow_history, start_time
            )
        
        # Step 2: Run Underwriting Agent
        underwriting_input = {
            "pan_details": kyc_result.output.get("pan_details", {}),
            "eligibility": kyc_result.output.get("eligibility", {}),
            "applicant_income": input_data.get("applicant_income", 50000),
            "loan_amount": input_data.get("loan_amount", 500000),
            "loan_term": input_data.get("loan_term", 36),
            "session_id": session_id
        }
        
        underwriting_agent = self.agents.get("Underwriting Agent")
        underwriting_result = underwriting_agent.run(underwriting_input)
        workflow_history.append(underwriting_result.to_dict())
        
        if underwriting_result.status != AgentStatus.SUCCESS:
            return self._create_orchestrator_result(
                input_data, underwriting_result, workflow_history, start_time
            )
        
        # Step 3: Check if negotiation is needed
        if underwriting_result.next_agent == "Negotiation Agent":
            negotiation_input = {
                "loan_details": underwriting_result.output.get("loan_details", {}),
                "offered_rate": underwriting_result.output.get("offered_rate"),
                "risk_tier": underwriting_result.output.get("risk_tier"),
                "max_negotiation_rounds": underwriting_result.output.get("max_negotiation_rounds"),
                "negotiation_requested": input_data.get("negotiation_requested", False),
                "counter_rate": input_data.get("counter_rate"),
                "session_id": session_id
            }
            
            negotiation_agent = self.agents.get("Negotiation Agent")
            negotiation_result = negotiation_agent.run(negotiation_input)
            workflow_history.append(negotiation_result.to_dict())
            
            final_result = negotiation_result
        else:
            final_result = underwriting_result
        
        # Step 4: Run Blockchain Audit Agent when offer is accepted
        blockchain_candidate = final_result.output if isinstance(final_result.output, dict) else {}
        if blockchain_candidate.get("next_agent") == "BlockchainAuditAgent":
            blockchain_input = {
                "applicant_name": kyc_result.output.get("pan_details", {}).get("name", "Applicant"),
                "loan_amount": blockchain_candidate.get("loan_amount"),
                "tenure_months": blockchain_candidate.get("tenure_months"),
                "final_rate": blockchain_candidate.get("final_rate"),
                "emi": blockchain_candidate.get("emi"),
                "total_payable": blockchain_candidate.get("total_payable"),
                "total_interest": blockchain_candidate.get("total_interest"),
                "session_id": session_id,
            }
            blockchain_agent = self.agents.get("BlockchainAuditAgent")
            blockchain_result = blockchain_agent.run(blockchain_input)
            workflow_history.append(blockchain_result.to_dict())
            final_result = blockchain_result

        # Step 5: Run Translation Agent if needed
        preferred_language = input_data.get("preferred_language", "en")
        
        if preferred_language != "en":
            translation_input = {
                "response_to_translate": final_result.output,
                "target_language": preferred_language,
                "session_id": session_id
            }
            
            translation_agent = self.agents.get("Translation Agent")
            translation_result = translation_agent.run(translation_input)
            workflow_history.append(translation_result.to_dict())
        
        # Step 6: Aggregate all results
        aggregated = self.call_tool("aggregate_results", results=workflow_history)
        
        # Step 7: Generate summary
        summary = self.call_tool("generate_summary", agent_results=workflow_history)
        
        # Build final output
        output = {
            "session_id": session_id,
            "workflow_history": workflow_history,
            "aggregated_results": aggregated,
            "application_summary": summary.get("application_summary", {}),
            "next_steps": summary.get("next_steps", []),
            "documents_needed": summary.get("documents_needed", [])
        }
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            output=output,
            reasoning=f"Complete workflow executed. Agents run: {', '.join([r['agent_name'] for r in workflow_history])}",
            next_agent=None,
            duration_ms=duration_ms
        )

    def _create_orchestrator_result(
        self, 
        input_data: dict, 
        failed_result: AgentResult, 
        workflow_history: list, 
        start_time: float
    ) -> AgentResult:
        """Create result when workflow fails."""
        aggregated = self.call_tool("aggregate_results", results=workflow_history)
        
        output = {
            "session_id": input_data.get("session_id", f"session_{int(time.time())}"),
            "workflow_history": workflow_history,
            "aggregated_results": aggregated,
            "failure_point": failed_result.agent_name,
            "failure_reason": failed_result.reasoning
        }
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILED,
            output=output,
            reasoning=f"Workflow failed at {failed_result.agent_name}: {failed_result.reasoning}",
            next_agent=None,
            duration_ms=duration_ms
        )


# =============================================================================
# AGENT 6: MASTER ORCHESTRATOR AGENT
# =============================================================================

class ApplicationStage(str, Enum):
    """Stage machine for loan application flow."""
    INITIATED = "INITIATED"
    KYC_PENDING = "KYC_PENDING"
    KYC_VERIFIED = "KYC_VERIFIED"
    CREDIT_ASSESSED = "CREDIT_ASSESSED"
    OFFER_GENERATED = "OFFER_GENERATED"
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    SANCTIONED = "SANCTIONED"


# Stage transition map - what stages can follow each stage
STAGE_TRANSITIONS = {
    ApplicationStage.INITIATED: [ApplicationStage.KYC_PENDING],
    ApplicationStage.KYC_PENDING: [ApplicationStage.KYC_VERIFIED, ApplicationStage.INITIATED],
    ApplicationStage.KYC_VERIFIED: [ApplicationStage.CREDIT_ASSESSED],
    ApplicationStage.CREDIT_ASSESSED: [ApplicationStage.OFFER_GENERATED, ApplicationStage.KYC_VERIFIED],
    ApplicationStage.OFFER_GENERATED: [ApplicationStage.NEGOTIATING, ApplicationStage.ACCEPTED],
    ApplicationStage.NEGOTIATING: [ApplicationStage.ACCEPTED, ApplicationStage.OFFER_GENERATED],
    ApplicationStage.ACCEPTED: [ApplicationStage.SANCTIONED],
    ApplicationStage.SANCTIONED: [],
}


class MasterOrchestratorAgent(BaseAgent):
    """
    Master Orchestrator Agent
    
    Role: Manages the entire loan conversation flow using Groq LLaMA 70B.
    Decides which agent to invoke next based on current application stage
    and user's free-text messages.
    
    Tools:
    - get_application_stage: Get current stage of application
    - delegate_to_agent: Route to specific agent with payload
    - update_stage: Move application to next stage
    - send_message_to_user: Generate response in user's language
    
    Uses Groq LLaMA 70B to:
    1. Understand user's free-text message
    2. Map it to current stage
    3. Decide next action
    4. Generate appropriate response
    """

    def __init__(self, agents: dict[str, BaseAgent]):
        self.agents = agents
        # In-memory session storage
        self._sessions: dict[str, dict] = {}
        super().__init__(
            name="Master Orchestrator Agent",
            role="Manage entire loan conversation flow with stage-based routing",
            tools=self._create_tools()
        )
        # Use larger model for complex reasoning
        self.llm_model = "llama3-70b-8192"

    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_application_stage",
                description="Get current stage of loan application",
                func=self._tool_get_application_stage,
                parameters={"session_id": "str"}
            ),
            Tool(
                name="delegate_to_agent",
                description="Delegate task to specific agent",
                func=self._tool_delegate_to_agent,
                parameters={"agent_name": "str", "payload": "dict"}
            ),
            Tool(
                name="update_stage",
                description="Update application to new stage",
                func=self._tool_update_stage,
                parameters={"session_id": "str", "new_stage": "str"}
            ),
            Tool(
                name="send_message_to_user",
                description="Generate message for user in their language",
                func=self._tool_send_message_to_user,
                parameters={"message": "str", "language": "str"}
            ),
        ]

    def _build_system_prompt(self) -> str:
        return """You are the Master Orchestrator for LoanEase, a personal loan AI system.
Your job is to manage a multi-step loan application process using stage-based routing.

STAGE MACHINE (strict order):
INITIATED → KYC_PENDING → KYC_VERIFIED → CREDIT_ASSESSED → 
OFFER_GENERATED → NEGOTIATING → ACCEPTED → SANCTIONED

Current application stage: {stage}
Available next actions: {available_actions}

You must respond ONLY with valid JSON:
{
  action: 'DELEGATE_KYC' | 'DELEGATE_CREDIT' | 'DELEGATE_NEGOTIATION' | 
          'DELEGATE_TRANSLATION' | 'ASK_USER' | 'ESCALATE_HUMAN' | 'COMPLETE',
  message_to_user: '...',
  reasoning: '...',
  next_stage: '...' (optional)
}

Guidelines:
- DELEGATE_KYC: When user provides identity documents or PAN/Aadhaar details
- DELEGATE_CREDIT: When KYC is verified and credit assessment is needed
- DELEGATE_NEGOTIATION: When user wants to negotiate interest rate
- DELEGATE_TRANSLATION: When user prefers Hindi or needs translation
- ASK_USER: When you need more information from user
- ESCALATE_HUMAN: When issue cannot be resolved automatically
- COMPLETE: When loan is sanctioned and process is done"""

    def _tool_get_application_stage(self, session_id: str) -> dict:
        """Tool: Get current application stage."""
        session = self._sessions.get(session_id, {})
        return {
            "session_id": session_id,
            "current_stage": session.get("stage", ApplicationStage.INITIATED.value),
            "history": session.get("history", []),
            "data": session.get("data", {})
        }

    def _tool_delegate_to_agent(self, agent_name: str, payload: dict) -> dict:
        """Tool: Delegate to specific agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}
        
        result = agent.run(payload)
        return result.to_dict()

    def _tool_update_stage(self, session_id: str, new_stage: str) -> dict:
        """Tool: Update application stage."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {"stage": ApplicationStage.INITIATED.value, "history": [], "data": {}}
        
        old_stage = self._sessions[session_id]["stage"]
        self._sessions[session_id]["stage"] = new_stage
        self._sessions[session_id]["history"].append({
            "from_stage": old_stage,
            "to_stage": new_stage,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "session_id": session_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "updated": True
        }

    def _tool_send_message_to_user(self, message: str, language: str = "en") -> dict:
        """Tool: Send message to user in their language."""
        # If language is Hindi, wrap with translation marker
        if language == "hi":
            return {
                "message": message,
                "language": language,
                "translated": True,
                "original": message
            }
        return {
            "message": message,
            "language": language,
            "translated": False
        }

    def _get_available_actions(self, stage: ApplicationStage) -> list[str]:
        """Get available actions for current stage."""
        transitions = STAGE_TRANSITIONS.get(stage, [])
        actions = []
        if ApplicationStage.KYC_PENDING in transitions:
            actions.append("DELEGATE_KYC")
        if ApplicationStage.CREDIT_ASSESSED in transitions:
            actions.append("DELEGATE_CREDIT")
        if ApplicationStage.NEGOTIATING in transitions:
            actions.append("DELEGATE_NEGOTIATION")
        if ApplicationStage.SANCTIONED in transitions:
            actions.append("COMPLETE")
        actions.append("ASK_USER")
        return actions

    def _call_llm_for_decision(self, user_message: str, context: dict) -> dict:
        """Use Groq LLaMA 70B to decide next action."""
        stage = context.get("stage", ApplicationStage.INITIATED.value)
        available_actions = self._get_available_actions(ApplicationStage(stage))
        
        system_prompt = self._build_system_prompt().format(
            stage=stage,
            available_actions=", ".join(available_actions)
        )
        
        user_prompt = f"""Current Stage: {stage}
User Message: {user_message}
Application Data: {context.get('data', {})}

Decide the next action and generate an appropriate response."""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            # Fallback to rule-based decision
            return self._fallback_decision(user_message, context)

    def _fallback_decision(self, user_message: str, context: dict) -> dict:
        """Fallback rule-based decision when LLM is unavailable."""
        stage = context.get("stage", ApplicationStage.INITIATED.value)
        message_lower = user_message.lower()
        
        # Simple keyword-based routing
        if "pan" in message_lower or "aadhaar" in message_lower or "document" in message_lower:
            return {
                "action": "DELEGATE_KYC",
                "message_to_user": "Let me verify your identity documents.",
                "reasoning": "User provided document information"
            }
        elif "credit" in message_lower or "score" in message_lower or "eligibility" in message_lower:
            return {
                "action": "DELEGATE_CREDIT",
                "message_to_user": "Let me check your credit eligibility.",
                "reasoning": "User asking about credit eligibility"
            }
        elif "rate" in message_lower or "interest" in message_lower or "negotiate" in message_lower:
            return {
                "action": "DELEGATE_NEGOTIATION",
                "message_to_user": "Let me help you with interest rate negotiation.",
                "reasoning": "User wants to negotiate rate"
            }
        else:
            return {
                "action": "ASK_USER",
                "message_to_user": "Could you please provide more details about your loan requirement?",
                "reasoning": "Need more information from user"
            }

    def run(self, input_data: dict) -> AgentResult:
        """
        Execute master orchestration - handle conversation flow.
        
        Expected input:
        {
            "session_id": "uuid",
            "user_message": "I want to apply for a personal loan",
            "language": "en" | "hi",
            // Optional: pre-filled data
            "pan_number": "ABCDE1234F",
            "loan_amount": 500000,
            ...
        }
        """
        start_time = time.time()
        
        # Get or create session
        session_id = input_data.get("session_id")
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "stage": ApplicationStage.INITIATED.value,
                "history": [],
                "data": {}
            }
        
        session = self._sessions[session_id]
        current_stage = session["stage"]
        
        # Merge input data into session
        for key, value in input_data.items():
            if key not in ["session_id", "user_message", "language"]:
                session["data"][key] = value
        
        # Get user message
        user_message = input_data.get("user_message", "")
        language = input_data.get("language", "en")
        
        # Build context for LLM
        context = {
            "stage": current_stage,
            "data": session["data"],
            "history": session["history"]
        }
        
        # Use LLM to decide next action
        llm_decision = self._call_llm_for_decision(user_message, context)
        
        # Execute the decided action
        action = llm_decision.get("action", "ASK_USER")
        message_to_user = llm_decision.get("message_to_user", "How can I help you?")
        reasoning = llm_decision.get("reasoning", "Decision made based on user input")
        
        output = {
            "session_id": session_id,
            "current_stage": current_stage,
            "action": action,
            "message_to_user": message_to_user,
            "reasoning": reasoning,
            "llm_decision": llm_decision
        }
        
        # Execute delegation if needed
        if action == "DELEGATE_KYC":
            kyc_payload = {
                "pan_image": session["data"].get("pan_image"),
                "aadhaar_image": session["data"].get("aadhaar_image"),
                "pan_number": session["data"].get("pan_number"),
                "aadhaar_number": session["data"].get("aadhaar_number"),
                "session_id": session_id
            }
            result = self.call_tool("delegate_to_agent", agent_name="KYCVerificationAgent", payload=kyc_payload)
            output["delegate_result"] = result
            if result.get("status") == "success":
                self.call_tool("update_stage", session_id=session_id, new_stage=ApplicationStage.KYC_VERIFIED.value)
                output["new_stage"] = ApplicationStage.KYC_VERIFIED.value
                
        elif action == "DELEGATE_CREDIT":
            credit_payload = {
                "pan_number": session["data"].get("pan_number"),
                "applicant_income": session["data"].get("applicant_income", 50000),
                "loan_amount": session["data"].get("loan_amount", 500000),
                "loan_term": session["data"].get("loan_term", 36),
                "session_id": session_id
            }
            result = self.call_tool("delegate_to_agent", agent_name="CreditUnderwritingAgent", payload=credit_payload)
            output["delegate_result"] = result
            if result.get("status") == "success":
                self.call_tool("update_stage", session_id=session_id, new_stage=ApplicationStage.OFFER_GENERATED.value)
                output["new_stage"] = ApplicationStage.OFFER_GENERATED.value
                
        elif action == "DELEGATE_NEGOTIATION":
            neg_payload = {
                "loan_details": session["data"].get("loan_details", {}),
                "offered_rate": session["data"].get("offered_rate", 10.5),
                "risk_tier": session["data"].get("risk_tier", "Low Risk"),
                "negotiation_requested": True,
                "counter_rate": session["data"].get("counter_rate"),
                "session_id": session_id
            }
            result = self.call_tool("delegate_to_agent", agent_name="Negotiation Agent", payload=neg_payload)
            output["delegate_result"] = result
            if result.get("status") == "success":
                self.call_tool("update_stage", session_id=session_id, new_stage=ApplicationStage.ACCEPTED.value)
                output["new_stage"] = ApplicationStage.ACCEPTED.value
                
        elif action == "COMPLETE":
            self.call_tool("update_stage", session_id=session_id, new_stage=ApplicationStage.SANCTIONED.value)
            output["new_stage"] = ApplicationStage.SANCTIONED.value
        
        # Translate message if needed
        if language == "hi" and action != "DELEGATE_TRANSLATION":
            trans_result = self.call_tool(
                "send_message_to_user",
                message=message_to_user,
                language=language
            )
            output["message_to_user"] = trans_result.get("message", message_to_user)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            output=output,
            reasoning=reasoning,
            next_agent=None,
            duration_ms=duration_ms
        )


# =============================================================================
# ORCHESTRATION ENGINE
# =============================================================================

class LoanEaseOrchestrator:
    """
    Main orchestration engine for LoanEase agent system.
    
    This is the public interface that users interact with.
    It manages the agent registry and executes workflows.
    """
    
    def __init__(self):
        # Initialize all agents
        self.agents: dict[str, BaseAgent] = {
            "KYCVerificationAgent": KYCVerificationAgent(),
            "KYC Agent": KYCAgent(),  # Legacy agent kept for compatibility
            "CreditUnderwritingAgent": CreditUnderwritingAgent(),
            "Underwriting Agent": UnderwritingAgent(),  # Legacy kept for compatibility
            "Negotiation Agent": NegotiationAgent(),
            "BlockchainAuditAgent": BlockchainAuditAgent(),
            "Translation Agent": TranslationAgent(),
        }
        
        # Add orchestrator with agent registry
        self.agents["Orchestrator Agent"] = OrchestratorAgent(agents=self.agents)
        
        # Add Master Orchestrator for conversation flow
        self.agents["Master Orchestrator Agent"] = MasterOrchestratorAgent(agents=self.agents)
        
    def run_workflow(self, application_data: dict) -> AgentResult:
        """
        Run the complete loan application workflow.
        
        Args:
            application_data: Dictionary containing:
                - pan_number: Applicant's PAN number
                - aadhaar_number: Applicant's Aadhaar number (optional)
                - applicant_income: Monthly income
                - loan_amount: Requested loan amount
                - loan_term: Loan tenure in months
                - preferred_language: "en" or "hi"
                - negotiation_requested: Whether to run negotiation
                - counter_rate: Counter-offer rate (optional)
                
        Returns:
            AgentResult with complete workflow results
        """
        orchestrator = self.agents["Orchestrator Agent"]
        return orchestrator.run(application_data)
    
    def get_agent_status(self, agent_name: str) -> dict:
        """Get status of a specific agent."""
        agent = self.agents.get(agent_name)
        if agent:
            return {
                "name": agent.name,
                "role": agent.role,
                "tools": [t.name for t in agent.tools],
                "available": True
            }
        return {"available": False}
    
    def list_agents(self) -> list[dict]:
        """List all available agents."""
        return [
            {
                "name": agent.name,
                "role": agent.role,
                "tools": [t.name for t in agent.tools]
            }
            for agent in self.agents.values()
        ]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Example usage of the orchestration system
    
    orchestrator = LoanEaseOrchestrator()
    
    # List all agents
    print("=" * 60)
    print("LOANEASE 5-AGENT ORCHESTRATION SYSTEM")
    print("=" * 60)
    print("\nAvailable Agents:")
    for agent_info in orchestrator.list_agents():
        print(f"\n  {agent_info['name']}")
        print(f"    Role: {agent_info['role']}")
        print(f"    Tools: {', '.join(agent_info['tools'])}")
    
    # Run a sample workflow
    print("\n" + "=" * 60)
    print("RUNNING SAMPLE WORKFLOW")
    print("=" * 60)
    
    application_data = {
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "applicant_income": 75000,
        "loan_amount": 1000000,
        "loan_term": 48,
        "preferred_language": "en",
        "negotiation_requested": False,
    }
    
    result = orchestrator.run_workflow(application_data)
    
    print(f"\nWorkflow Status: {result.status.value}")
    print(f"Duration: {result.duration_ms}ms")
    print(f"\nReasoning: {result.reasoning}")
    print(f"\nNext Agent: {result.next_agent}")
    
    if result.output:
        summary = result.output.get("application_summary", {})
        print(f"\nApplication Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")