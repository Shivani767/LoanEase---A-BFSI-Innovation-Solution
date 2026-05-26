import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.groq_service import GroqService, get_groq_service

logger = logging.getLogger("loanease.groq")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    language: str = "en"

class ChatResponse(BaseModel):
    message: str
    action: str = "ASK_USER"
    confidence: float = 0.5
    session_id: str
    language: str
    model_used: Optional[str] = None
    fallback_used: Optional[bool] = None
    response_time_ms: Optional[int] = None

class TranslateRequest(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str = "hi"

class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    confidence: float

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, groq: GroqService = Depends(get_groq_service)):
    """Chat with AI assistant"""
    start_time = asyncio.get_event_loop().time()

    try:
        system_prompt = "You are a helpful loan assistant. Be concise and professional."
        if request.language == "hi":
            system_prompt = "आप एक सहायक ऋण सहायक हैं। संक्षिप्त और पेशेवर रहें।"

        reply, _trace = await groq.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": request.message}],
        )

        response_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        status = groq.status()

        return ChatResponse(
            message=reply,
            session_id=request.session_id,
            language=request.language,
            model_used=status.get("model"),
            fallback_used=status.get("fallback_used"),
            response_time_ms=response_time_ms,
        )

    except Exception as e:
        logger.error("Chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Chat service unavailable")

@router.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(
    request: TranslateRequest,
    groq: GroqService = Depends(get_groq_service),
):
    """Translate text using Groq"""
    try:
        if request.source_language == request.target_language:
            return TranslateResponse(
                translated_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                confidence=1.0,
            )

        prompt = (
            "Translate the following text from "
            f"{request.source_language} to {request.target_language}. "
            "Only return the translation, no explanations."
        )
        translated, _trace = await groq.chat(
            system_prompt=prompt,
            messages=[{"role": "user", "content": request.text}],
        )

        status = groq.status()
        return TranslateResponse(
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=0.3 if status.get("fallback_used") else 0.8,
        )

    except Exception as e:
        logger.error("Translation error: %s", e)
        raise HTTPException(status_code=500, detail="Translation service unavailable")

@router.get("/health")
async def groq_health():
    """Groq service health check"""
    try:
        # Simple health check without dependency injection
        return {
            "connected": False,
            "model": None,
            "fallback_used": True,
            "status": "Groq service initialized"
        }
    except Exception as e:
        return {
            "connected": False,
            "model": None,
            "fallback_used": True,
            "status": f"Groq service error: {str(e)}"
        }
