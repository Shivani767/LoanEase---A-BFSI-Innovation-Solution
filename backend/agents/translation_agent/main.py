from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.groq_service import GroqService, get_groq_service

logger = logging.getLogger("loanease.translation")

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str = "hi"


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    confidence: float


class IntentRequest(BaseModel):
    message: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(
    request: TranslateRequest,
    groq: GroqService = Depends(get_groq_service),
) -> TranslateResponse:
    """Translate text using Groq LLM."""
    try:
        if request.source_language == request.target_language:
            return TranslateResponse(
                translated_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                confidence=1.0,
            )

        system_prompt = (
            "Translate the following text from "
            f"{request.source_language} to {request.target_language}. "
            "Return only the translation."
        )
        translated, _trace = await groq.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": request.text}],
        )

        status = groq.status()
        confidence = 0.3 if status.get("fallback_used") else 0.8
        return TranslateResponse(
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=confidence,
        )
    except Exception as exc:
        logger.error("Translation error: %s", exc)
        raise HTTPException(status_code=500, detail="Translation service unavailable")


@router.post("/detect-hinglish-intent")
async def detect_hinglish_intent(
    request: IntentRequest,
    groq: GroqService = Depends(get_groq_service),
) -> Dict[str, Any]:
    """Detect intent from Hinglish input using Groq fast model."""
    try:
        system_prompt = (
            "Classify the intent of the user message and return JSON only. "
            "Allowed intents: LOAN_REQUEST, RATE_QUERY, COUNTER_REQUEST, ACCEPTANCE, CANCELLATION, KYC_PROMPT, UNKNOWN. "
            "Return format: {\"intent\": \"...\"}."
        )
        return await groq.route_intent(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": request.message}],
            temperature=0.0,
            max_tokens=128,
        )
    except Exception as exc:
        logger.error("Intent detection error: %s", exc)
        raise HTTPException(status_code=500, detail="Intent detection unavailable")

@router.get("/health")
async def translation_health():
    """Translation service health check"""
    return {
        "status": "healthy",
        "service": "translation_agent",
        "groq_integration": True
    }
