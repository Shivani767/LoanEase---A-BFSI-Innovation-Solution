import math
from typing import Dict, Tuple
from core.config import settings

def calculate_emi(
    principal: float, 
    annual_rate: float, 
    tenure_years: int
) -> Dict:
    """Calculate EMI and related loan details"""
    
    # Convert annual rate to monthly
    monthly_rate = annual_rate / 12 / 100
    
    # Calculate number of months
    tenure_months = tenure_years * 12
    
    # EMI calculation
    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
    
    # Total payment and interest
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    
    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_years": tenure_years,
        "monthly_emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_rate_percentage": round((total_interest / principal) * 100, 2)
    }

def calculate_affordability(
    monthly_income: float,
    existing_emi: float = 0,
    max_dti_ratio: float = 0.5  # 50% debt-to-income ratio
) -> Dict:
    """Calculate maximum affordable loan amount"""
    
    # Maximum EMI based on income
    max_emi = monthly_income * max_dti_ratio - existing_emi
    
    if max_emi <= 0:
        return {
            "max_loan_amount": 0,
            "max_emi": 0,
            "affordable": False
        }
    
    # Estimate maximum loan (assuming 12% rate for 5 years)
    estimated_rate = 12.0
    estimated_tenure = 5
    
    # Reverse EMI calculation
    monthly_rate = estimated_rate / 12 / 100
    tenure_months = estimated_tenure * 12
    
    if monthly_rate == 0:
        max_loan = max_emi * tenure_months
    else:
        max_loan = max_emi * ((1 + monthly_rate) ** tenure_months - 1) / (monthly_rate * (1 + monthly_rate) ** tenure_months)
    
    return {
        "max_loan_amount": round(max_loan, 2),
        "max_emi": round(max_emi, 2),
        "affordable": max_loan > 100000,  # Minimum loan threshold
        "assumed_rate": estimated_rate,
        "assumed_tenure": estimated_tenure
    }

from services.conversation_context import PURPOSE_PROFILES

def calculate_negotiation_params(
    current_rate: float,
    risk_category: str,
    customer_profile: str = "STANDARD",
    purpose: str = None
) -> Dict:
    """Calculate negotiation parameters based on risk and profile"""
    
    # Base concession based on risk category
    risk_concessions = {
        "LOW": 1.5,
        "MEDIUM": 1.0,
        "MEDIUM-HIGH": 0.5,
        "HIGH": 0.0
    }
    
    # Profile multiplier
    profile_multipliers = {
        "EXCELLENT": 1.5,
        "GOOD": 1.2,
        "STANDARD": 1.0,
        "RISKY": 0.8
    }
    
    base_concession = risk_concessions.get(risk_category, 0.0)
    
    # Adjust for purpose (e.g. medical gets priority/better rate)
    if purpose and purpose in PURPOSE_PROFILES:
        profile = PURPOSE_PROFILES[purpose]
        if profile.get("processing") == "priority" or profile.get("urgency") == "high":
            base_concession += 0.5

    profile_multiplier = profile_multipliers.get(customer_profile, 1.0)
    
    max_concession = base_concession * profile_multiplier
    min_rate = max(settings.RATE_FLOOR, current_rate - max_concession)
    
    # Negotiation steps
    steps = []
    current_step = current_rate
    
    # If high urgency, allow larger jumps to close faster
    step_size = settings.CONCESSION_STEP
    if purpose and purpose in PURPOSE_PROFILES and PURPOSE_PROFILES[purpose].get("urgency") == "high":
        step_size *= 1.5
        
    while current_step > min_rate:
        current_step = max(min_rate, current_step - step_size)
        steps.append(current_step)
    
    return {
        "current_rate": current_rate,
        "min_rate": round(min_rate, 2),
        "max_concession": round(max_concession, 2),
        "negotiation_steps": [round(step, 2) for step in steps],
        "total_steps": len(steps)
    }

