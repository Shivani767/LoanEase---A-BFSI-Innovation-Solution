from __future__ import annotations

import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from groq import Groq, RateLimitError, APITimeoutError, APIConnectionError
except ImportError:
    print("Groq library not found. Install with: pip install groq")
    # Create mock classes for fallback
    class RateLimitError(Exception): pass
    class APITimeoutError(Exception): pass
    class APIConnectionError(Exception): pass
    class Groq:
        def __init__(self, api_key: str): pass


@dataclass
class GroqResponse:
    content: str
    model_used: str
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None


# =============================================================================
# HINGLISH SYSTEM PROMPT ADDENDUM
# =============================================================================

HINGLISH_SYSTEM_PROMPT_ADDENDUM = """
The user is typing Hindi in English letters (Hinglish). Respond in Hindi Devanagari script. Keep financial terms in English.
Example of ideal response tone:
'हाँ बिल्कुल! आपका loan ₹5,00,000 के लिए approve हो गया है। Rate 11.0% रहेगी।'
"""


# =============================================================================
# AGENT-SPECIFIC PROMPTS
# =============================================================================

MASTER_AGENT_PROMPT = """
You are the Master Orchestrator of LoanEase, an AI personal loan system for Indian borrowers.
You manage a multi-step loan pipeline.

Current application stage: {stage}
Applicant language: {language}
Completed steps: {completed_steps}

Your decisions:
- Understand user intent
- Decide which specialized agent to invoke
- Generate user-facing message in {language}
- Keep responses under 80 words
- Never make up loan rates or eligibility

Respond ONLY in this JSON format:
{{
  "action": "DELEGATE_KYC | DELEGATE_CREDIT | DELEGATE_NEGOTIATION | DELEGATE_BLOCKCHAIN | ASK_USER | ESCALATE_HUMAN",
  "user_message": "message in {language}",
  "reasoning": "internal reasoning",
  "confidence": 0.0-1.0
}}
"""

CREDIT_EXPLANATION_PROMPT = """
You are explaining a credit decision to an Indian loan applicant in {language}.

Applicant details:
- Credit score: {credit_score}/900
- Risk score: {risk_score}/100  
- Decision: {decision}
- Offered rate: {rate}%

Structured SHAP Analysis:
{structured_shap}

Write a warm, clear explanation (max 100 words) of why this decision was made.
Use simple language — not financial jargon.
If approved: be encouraging.
If rejected: be empathetic, give hope.
Mention the top 2 factors from SHAP with their actual values.
Keep financial terms (EMI, CIBIL, KYC) in English even in Hindi responses.
Never say "your XGBoost score" — say "your financial profile".
"""

NEGOTIATION_REASONING_PROMPT = """
You are a loan negotiation agent explaining a rate decision to an applicant in {language}.

Negotiation context:
- Starting rate: {starting_rate}%
- Current offer: {current_rate}%
- Floor rate: {floor_rate}%
- Round: {round} of {max_rounds}
- Risk tier: {risk_tier}
- Key strength: {top_positive_shap_factor}

Write a 2-3 sentence explanation (max 60 words) of why you're offering this specific rate.
Sound like a helpful bank relationship manager.
Be specific — mention their actual risk tier and the factor that helped them.
"""

REJECTION_EMPATHY_PROMPT = """
Write an empathetic rejection message in {language} for a loan applicant whose credit score of {score} is below 300.

Include:
1. Acknowledge their situation (1 sentence)
2. Explain the minimum requirement (1 sentence)  
3. Give 3 specific actionable tips to improve their score
4. End with encouragement to reapply in 6 months

Tone: warm, supportive, not robotic.
Max 120 words.
Financial terms stay in English.
"""

INTENT_CLASSIFICATION_PROMPT = """
Classify this loan chatbot message into exactly one intent. Message: '{text}'

Intents:
LOAN_REQUEST, RATE_QUERY, COUNTER_REQUEST,
ACCEPTANCE, REJECTION, KYC_READY,
ESCALATION_REQUEST, EMI_QUERY,
ELIGIBILITY_QUERY, TENURE_CHANGE,
GENERAL_QUERY

Also extract any numbers mentioned (loan amounts, rates, tenures).
Detect language: 'en' | 'hi' | 'hinglish_latin' | 'hindi_devanagari'

Respond ONLY with JSON:
{{
  'intent': '...',
  'confidence': 0.0-1.0,
  'language': 'en'|'hi'|'hinglish_latin'|'hindi_devanagari',
  'extracted': {{
    'amount': null or number,
    'rate': null or number,
    'tenure': null or number
  }}
}}
"""


class GroqClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found in environment variables")
        
        try:
            self.client = Groq(api_key=self.api_key or "dummy_key")
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            self.client = None
            
        self.primary_model = os.getenv("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile")
        self.fallback_model = os.getenv("GROQ_MODEL_FALLBACK", "llama-3.1-8b-instant")
        self.timeout_seconds = int(os.getenv("GROQ_TIMEOUT_SECONDS", "8"))
        self.fallback_mode = os.getenv("FALLBACK_MODE", "rule_based")
        
        self.request_count = 0
        self.fallback_count = 0
        self.error_log: List[str] = []
        self.start_time = datetime.now(timezone.utc)
    
    async def complete(self,
                     messages: List[Dict[str, str]],
                     max_tokens: int = 400,
                     temperature: float = 0.3,
                     require_json: bool = False,
                     input_style: Optional[str] = None) -> GroqResponse:
        """
        Complete a chat request with automatic fallback handling.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            require_json: Whether to require JSON output format.
            input_style: Optional input style hint ('hinglish_latin', 'hindi_devanagari', 'english').
                         When 'hinglish_latin', appends Hinglish instructions to system prompt.
        """
        start_time = datetime.now()
        
        # Prepend Hinglish addendum if needed
        if input_style == "hinglish_latin" and messages:
            # Find system message and append Hinglish instructions
            modified_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    modified_content = msg["content"] + "\n\n" + HINGLISH_SYSTEM_PROMPT_ADDENDUM
                    modified_messages.append({"role": "system", "content": modified_content})
                else:
                    modified_messages.append(msg)
            messages = modified_messages
        
        # Try primary model first
        try:
            if not self.client:
                raise APIConnectionError("Groq client not initialized")
                
            response = await self._call_groq(
                model=self.primary_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                require_json=require_json
            )
            self.request_count += 1
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return GroqResponse(
                content=response,
                model_used=self.primary_model,
                fallback_used=False,
                tokens_used=self._estimate_tokens(messages + [{"role": "assistant", "content": response}]),
                response_time_ms=int(response_time)
            )
        
        except RateLimitError:
            # Rate limited — try fallback model
            return await self._try_fallback(
                messages, max_tokens, temperature, require_json,
                reason="rate_limit", start_time=start_time
            )
        
        except APITimeoutError:
            # Timeout — try fallback model
            return await self._try_fallback(
                messages, max_tokens, temperature, require_json,
                reason="timeout", start_time=start_time
            )
        
        except APIConnectionError:
            # No internet — use rule-based fallback
            return self._rule_based_fallback(
                messages, reason="no_connection", start_time=start_time
            )
        
        except Exception as e:
            self.error_log.append(f"{datetime.now()}: {str(e)}")
            return self._rule_based_fallback(
                messages, reason="unknown_error", start_time=start_time
            )
    
    async def _call_groq(self, model: str, messages: List[Dict[str, str]], 
                        max_tokens: int, temperature: float, 
                        require_json: bool = False) -> str:
        """Make actual API call to Groq"""
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.client.chat.completions.create(**kwargs)
        )
        
        return response.choices[0].message.content
    
    async def _try_fallback(self, messages: List[Dict[str, str]], 
                           max_tokens: int, temperature: float, 
                           require_json: bool, reason: str, 
                           start_time: datetime) -> GroqResponse:
        """Try fallback model when primary fails"""
        try:
            response = await self._call_groq(
                model=self.fallback_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                require_json=require_json
            )
            self.fallback_count += 1
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return GroqResponse(
                content=response,
                model_used=self.fallback_model,
                fallback_used=True,
                fallback_reason=reason,
                tokens_used=self._estimate_tokens(messages + [{"role": "assistant", "content": response}]),
                response_time_ms=int(response_time)
            )
        except Exception as e:
            self.error_log.append(f"{datetime.now()}: Fallback failed for {reason}: {str(e)}")
            return self._rule_based_fallback(
                messages, reason=f"fallback_also_failed_{reason}", start_time=start_time
            )
    
    def _rule_based_fallback(self, messages: List[Dict[str, str]], 
                            reason: str, start_time: datetime) -> GroqResponse:
        """Rule-based fallback when Groq is unavailable"""
        # Extract last user message
        last_msg = messages[-1]["content"].lower() if messages else ""
        
        # Detect language using enhanced detection
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in last_msg)
        
        # Check Hinglish markers
        hinglish_markers = [
            "mujhe", "chahiye", "kitna", "kya", "hai", "hoga", "nahi", "theek",
            "bhai", "yaar", "aur", "kam", "zyada", "lena", "dena", "batao",
            "karo", "thoda", "bahut", "accha", "loan", "rate", "emi"
        ]
        hinglish_count = sum(1 for marker in hinglish_markers if marker in last_msg)
        is_hinglish = hinglish_count >= 2 and not has_devanagari
        
        # Determine language for fallback response
        if has_devanagari or is_hinglish:
            lang = "hi"
        else:
            lang = "en"
        
        # Map to hardcoded responses by keywords
        fallback_responses = {
            "loan": {
                "en": "I'll help you with your loan application. Please share your details to get started.",
                "hi": "मैं आपके loan में मदद करूँगा। शुरू करने के लिए अपनी जानकारी दें।"
            },
            "rate": {
                "en": "Your interest rate will be determined after credit assessment. Rates range from 10.5% to 14% based on profile.",
                "hi": "आपकी interest rate credit assessment के बाद तय होगी।"
            },
            "emi": {
                "en": "Your EMI depends on loan amount, rate, and tenure. Use our EMI calculator for exact figures.",
                "hi": "आपकी EMI loan राशि, दर और अवधि पर निर्भर करती है।"
            },
            "kyc": {
                "en": "Please upload your PAN card and Aadhaar card to proceed with KYC verification.",
                "hi": "KYC के लिए PAN card और Aadhaar card upload करें।"
            },
            "pan": {
                "en": "Please upload your PAN card to continue with the loan application.",
                "hi": "कृपया loan application जारी रखने के लिए अपना PAN card upload करें।"
            },
            "aadhaar": {
                "en": "Please upload your Aadhaar card for identity verification.",
                "hi": "पहचान सत्यापन के लिए कृपया अपना Aadhaar card upload करें।"
            },
            "default": {
                "en": "I'm here to help with your loan application. How can I assist you today?",
                "hi": "मैं आपकी loan में मदद के लिए यहाँ हूँ। कैसे मदद करूँ?"
            }
        }
        
        # Find matching response
        for keyword, responses in fallback_responses.items():
            if keyword in last_msg:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                return GroqResponse(
                    content=responses[lang],
                    model_used="rule_based_fallback",
                    fallback_used=True,
                    fallback_reason=reason,
                    response_time_ms=int(response_time)
                )
        
        # Default response
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        return GroqResponse(
            content=fallback_responses["default"][lang],
            model_used="rule_based_fallback",
            fallback_used=True,
            fallback_reason=reason,
            response_time_ms=int(response_time)
        )
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return max(1, total_chars // 4)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health and usage statistics"""
        uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return {
            "groq_api_reachable": self.client is not None,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "requests_today": self.request_count,
            "fallback_activations": self.fallback_count,
            "fallback_reasons": self._get_fallback_reasons(),
            "estimated_tokens_used": self.request_count * 1250,  # Avg tokens per request
            "free_tier_limit": "6000 tokens/minute",
            "current_mode": "fallback" if self.fallback_count > self.request_count // 2 else "primary",
            "last_error": self.error_log[-1] if self.error_log else None,
            "uptime_seconds": int(uptime_seconds),
            "api_key_configured": bool(self.api_key)
        }
    
    def _get_fallback_reasons(self) -> List[str]:
        """Summarize fallback reasons"""
        if not self.error_log:
            return []
        
        reasons = {}
        for error in self.error_log[-10:]:  # Last 10 errors
            if "rate_limit" in error.lower():
                reasons["rate_limit"] = reasons.get("rate_limit", 0) + 1
            elif "timeout" in error.lower():
                reasons["timeout"] = reasons.get("timeout", 0) + 1
            elif "connection" in error.lower():
                reasons["connection"] = reasons.get("connection", 0) + 1
            else:
                reasons["other"] = reasons.get("other", 0) + 1
        
        return [f"{k} x{v}" for k, v in reasons.items()]


# Global instance for easy access
groq_client = GroqClient()

