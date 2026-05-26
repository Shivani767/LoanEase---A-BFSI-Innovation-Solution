from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.prompts import get_system_prompt
from services.conversation_memory import ConversationMemory, get_memory
from services.groq_service import GroqService, get_groq_service
from services.conversation_context import (
    build_context_updates,
    build_error_recovery,
    build_memory_prompt_block,
    build_nudge,
    low_confidence_clarification,
)

router = APIRouter(prefix="/ai", tags=["AI"])


STAGE_ORDER = ["kyc", "credit", "negotiation", "sanction"]
STAGE_TRIGGER_KEYWORDS: Dict[str, list[str]] = {
    "credit": ["credit", "eligible", "approval probability", "risk score", "interest rate"],
    "negotiation": ["emi", "concession", "counter offer", "tenure option", "negotiate"],
    "sanction": ["sanction", "final terms", "acceptance", "polygon blockchain", "letter"],
}

# Map router stage names to pipeline stage prompt keys
STAGE_TO_PIPELINE_KEY: Dict[str, str] = {
    "kyc": "KYC_PENDING",
    "credit": "CREDIT_ASSESSED",
    "negotiation": "NEGOTIATING",
    "sanction": "SANCTIONED",
}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    stage: str = "kyc"
    channel: Optional[str] = "web"
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    stage: str
    response: str
    xai_trace: Dict[str, Any]
    quick_replies: list[Dict[str, str]] = Field(default_factory=list)


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    language: str
    loan_type: str
    urgency: str
    summary: str


class NudgeResponse(BaseModel):
    session_id: str
    should_nudge: bool
    stage: str
    message: str | None = None
    quick_replies: list[Dict[str, str]] = Field(default_factory=list)


class IntentRequest(BaseModel):
    message: str = Field(..., min_length=1)


class SessionContextResponse(BaseModel):
    session_id: str
    stage: str
    messages: list[dict]
    context: Dict[str, Any]
    meta: Dict[str, Any]


class DeleteSessionResponse(BaseModel):
    session_id: str
    cleared: bool


def _sse(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _coerce_stage(stage: str) -> str:
    normalized = (stage or "kyc").strip().lower()
    if normalized not in STAGE_ORDER:
        return "kyc"
    return normalized


def _forward_stage_only(current_stage: str, generated_text: str) -> str:
    current = _coerce_stage(current_stage)
    current_index = STAGE_ORDER.index(current)
    text = generated_text.lower()

    candidate = current
    for stage_name, triggers in STAGE_TRIGGER_KEYWORDS.items():
        if any(trigger in text for trigger in triggers):
            if STAGE_ORDER.index(stage_name) > current_index:
                if STAGE_ORDER.index(stage_name) > STAGE_ORDER.index(candidate):
                    candidate = stage_name
    return candidate


def _get_pipeline_stage_key(router_stage: str) -> str:
    """Map router stage to pipeline stage prompt key for contextual behavior."""
    return STAGE_TO_PIPELINE_KEY.get(_coerce_stage(router_stage), "INITIATED")


def _normalize_question_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


async def _classify_user_intent(groq: GroqService, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    intent_prompt = (
        "Classify the user's loan-chat intent and return JSON only with keys: "
        "intent, confidence, language, loan_type, urgency, summary. "
        "Confidence must be a number from 0 to 1. Be conservative if the message is vague."
    )
    result = await groq.route_intent(
        system_prompt=intent_prompt,
        messages=[{"role": "user", "content": json.dumps({"message": message, "context": context}, ensure_ascii=False)}],
        temperature=0.0,
        max_tokens=256,
    )
    return result if isinstance(result, dict) else {}


def _safe_confidence(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@router.post("/chat")
async def chat_stream(
    payload: ChatRequest,
    groq: GroqService = Depends(get_groq_service),
    memory: ConversationMemory = Depends(get_memory),
) -> StreamingResponse:
    """Primary streaming AI chat endpoint returning SSE events."""
    session_id = payload.session_id or str(uuid4())
    requested_stage = _coerce_stage(payload.stage)
    pipeline_stage_key = _get_pipeline_stage_key(requested_stage)

    async def event_generator() -> AsyncGenerator[str, None]:
        full_text = ""
        xai_trace: Dict[str, Any] = {}
        next_stage = requested_stage
        quick_replies: list[Dict[str, str]] = []

        try:
            # Keep all operational logic inside the generator so we can emit SSE error
            # events instead of failing the HTTP stream.
            memory.get_or_create(session_id)
            memory.set_stage(session_id, requested_stage)
            memory.set_context(session_id, payload.context)
            memory.append_message(session_id, "user", payload.message)

            state = memory.get_state(session_id) or {}
            prompt_context = {**state.get("context", {}), **payload.context}
            derived_updates = build_context_updates(payload.message, prompt_context, requested_stage)
            prompt_context.update(derived_updates)
            prompt_context["questions_asked"] = _normalize_question_list(prompt_context.get("questions_asked"))
            prompt_context["conversation_memory_block"] = build_memory_prompt_block(prompt_context)
            await memory.update_context(session_id, prompt_context)

            intent_result = await _classify_user_intent(groq, payload.message, prompt_context)
            intent_name = str(intent_result.get("intent", prompt_context.get("intent", "UNKNOWN")) or "UNKNOWN")
            intent_confidence = _safe_confidence(intent_result.get("confidence", prompt_context.get("intent_confidence", 0.0)))
            prompt_context["intent"] = intent_name
            prompt_context["intent_confidence"] = intent_confidence
            prompt_context["previous_intent"] = prompt_context.get("previous_intent") or intent_name
            await memory.update_context(session_id, {
                "intent": intent_name,
                "intent_confidence": intent_confidence,
                "previous_intent": prompt_context["previous_intent"],
            })

            if intent_confidence < 0.65:
                clarification = low_confidence_clarification(prompt_context, intent_name, intent_confidence)
                quick_replies = clarification.get("quick_replies", [])
                full_text = clarification["message"]
                xai_trace = {
                    "stage": requested_stage,
                    "intent": intent_name,
                    "intent_confidence": intent_confidence,
                    "needs_clarification": True,
                    "quick_replies": quick_replies,
                }
                yield _sse({"type": "token", "content": full_text})
                yield _sse({"type": "xai", "trace": xai_trace})
                memory.set_stage(session_id, requested_stage)
                memory.append_message(session_id, "assistant", full_text)
                yield _sse({"type": "done", "session_id": session_id, "stage": requested_stage, "quick_replies": quick_replies, "meta": {"needs_clarification": True, "intent": intent_name, "intent_confidence": intent_confidence}})
                return

            system_prompt = get_system_prompt(
                requested_stage,
                prompt_context,
                current_stage=pipeline_stage_key,
                channel=payload.channel or "web"
            )
            messages = memory.get_messages(session_id)

            async for chunk in groq.stream_chat(system_prompt=system_prompt, messages=messages):
                if chunk.startswith("XAI_TRACE::"):
                    raw = chunk.replace("XAI_TRACE::", "", 1)
                    try:
                        xai_trace = json.loads(raw) if raw else {}
                    except json.JSONDecodeError:
                        xai_trace = {}
                    yield _sse({"type": "xai", "trace": xai_trace})
                    continue

                full_text += chunk
                yield _sse({"type": "token", "content": chunk})

            next_stage = _forward_stage_only(requested_stage, full_text)
            memory.set_stage(session_id, next_stage)
            memory.append_message(session_id, "assistant", full_text)
            yield _sse({"type": "done", "session_id": session_id, "stage": next_stage, "quick_replies": quick_replies, "meta": {"intent": intent_name, "intent_confidence": intent_confidence}})
        except Exception as exc:
            recovery = build_error_recovery(str(exc), payload.context)
            yield _sse({"type": "token", "content": recovery["message"]})
            yield _sse({"type": "xai", "trace": {"recovery_type": recovery.get("recovery_type"), "quick_replies": recovery.get("quick_replies", [])}})
            memory.append_message(session_id, "assistant", recovery["message"])
            yield _sse({"type": "done", "session_id": session_id, "stage": requested_stage, "quick_replies": recovery.get("quick_replies", []), "meta": {"recovery_type": recovery.get("recovery_type")}})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Session-Id": session_id,
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(
    payload: ChatRequest,
    groq: GroqService = Depends(get_groq_service),
    memory: ConversationMemory = Depends(get_memory),
) -> ChatResponse:
    """Non-streaming fallback endpoint for tests and local debugging."""
    session_id = payload.session_id or str(uuid4())
    stage = _coerce_stage(payload.stage)
    pipeline_stage_key = _get_pipeline_stage_key(stage)

    memory.get_or_create(session_id)
    memory.set_stage(session_id, stage)
    memory.set_context(session_id, payload.context)
    memory.append_message(session_id, "user", payload.message)

    state = memory.get_state(session_id) or {}
    prompt_context = {**state.get("context", {}), **payload.context}
    derived_updates = build_context_updates(payload.message, prompt_context, stage)
    prompt_context.update(derived_updates)
    prompt_context["questions_asked"] = _normalize_question_list(prompt_context.get("questions_asked"))
    prompt_context["conversation_memory_block"] = build_memory_prompt_block(prompt_context)
    await memory.update_context(session_id, prompt_context)

    intent_result = await _classify_user_intent(groq, payload.message, prompt_context)
    intent_name = str(intent_result.get("intent", prompt_context.get("intent", "UNKNOWN")) or "UNKNOWN")
    intent_confidence = _safe_confidence(intent_result.get("confidence", prompt_context.get("intent_confidence", 0.0)))
    prompt_context["intent"] = intent_name
    prompt_context["intent_confidence"] = intent_confidence
    prompt_context["previous_intent"] = prompt_context.get("previous_intent") or intent_name
    await memory.update_context(session_id, {
        "intent": intent_name,
        "intent_confidence": intent_confidence,
        "previous_intent": prompt_context["previous_intent"],
    })

    if intent_confidence < 0.65:
        clarification = low_confidence_clarification(prompt_context, intent_name, intent_confidence)
        memory.set_stage(session_id, stage)
        memory.append_message(session_id, "assistant", clarification["message"])
        return ChatResponse(
            session_id=session_id,
            stage=stage,
            response=clarification["message"],
            xai_trace={
                "stage": stage,
                "intent": intent_name,
                "intent_confidence": intent_confidence,
                "needs_clarification": True,
                "quick_replies": clarification.get("quick_replies", []),
            },
            quick_replies=clarification.get("quick_replies", []),
        )

    system_prompt = get_system_prompt(
        stage,
        prompt_context,
        current_stage=pipeline_stage_key,
        channel=payload.channel or "web"
    )
    messages = memory.get_messages(session_id)

    response_text, xai_trace = await groq.chat(system_prompt=system_prompt, messages=messages)
    next_stage = _forward_stage_only(stage, response_text)

    memory.set_stage(session_id, next_stage)
    memory.append_message(session_id, "assistant", response_text)

    return ChatResponse(
        session_id=session_id,
        stage=next_stage,
        response=response_text,
        xai_trace={**xai_trace, "intent": intent_name, "intent_confidence": intent_confidence},
    )


@router.post("/intent", response_model=IntentResponse)
async def classify_intent(
    payload: IntentRequest,
    groq: GroqService = Depends(get_groq_service),
) -> IntentResponse:
    """Fast intent classification route using lightweight Groq model."""
    system_prompt = (
        "Classify the user message and return JSON only with keys: "
        "intent, confidence, language, loan_type, urgency, summary."
    )
    result = await groq.route_intent(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": payload.message}],
        temperature=0.0,
        max_tokens=256,
    )

    return IntentResponse(
        intent=str(result.get("intent", "UNKNOWN")),
        confidence=_safe_confidence(result.get("confidence", 0.5)),
        language=str(result.get("language", "unknown")),
        loan_type=str(result.get("loan_type", "unknown")),
        urgency=str(result.get("urgency", "normal")),
        summary=str(result.get("summary", payload.message[:120])),
    )


@router.get("/session/{session_id}/nudge", response_model=NudgeResponse)
async def get_session_nudge(
    session_id: str,
    memory: ConversationMemory = Depends(get_memory),
) -> NudgeResponse:
    state = memory.get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    context = state.get("context", {}) if isinstance(state, dict) else {}
    stage = str(state.get("stage", context.get("stage", "kyc")))
    nudge = build_nudge(stage, context)
    if not nudge:
        return NudgeResponse(session_id=session_id, should_nudge=False, stage=stage)

    if stage.lower() == "kyc":
        quick_replies = [
            {"label": "Upload documents", "value": "I'm ready to upload my documents"},
            {"label": "Need help", "value": "Can you help me with the KYC steps?"},
        ]
    elif stage.lower() == "credit":
        quick_replies = [
            {"label": "Explain offer", "value": "Explain the offer again"},
            {"label": "Continue", "value": "Let's continue"},
        ]
    else:
        quick_replies = [
            {"label": "Continue", "value": "Please continue"},
            {"label": "Explain", "value": "Explain the next step"},
        ]

    return NudgeResponse(
        session_id=session_id,
        should_nudge=True,
        stage=stage,
        message=nudge.get("message"),
        quick_replies=quick_replies,
    )


@router.delete("/session/{session_id}", response_model=DeleteSessionResponse)
async def clear_session(
    session_id: str,
    memory: ConversationMemory = Depends(get_memory),
) -> DeleteSessionResponse:
    """Clear all state for a session."""
    cleared = memory.clear(session_id)
    return DeleteSessionResponse(session_id=session_id, cleared=cleared)


@router.get("/session/{session_id}/ctx", response_model=SessionContextResponse)
async def inspect_session_context(
    session_id: str,
    memory: ConversationMemory = Depends(get_memory),
) -> SessionContextResponse:
    """Inspect full session context for debugging/admin."""
    if not memory.has_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    state = memory.get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionContextResponse(
        session_id=state.get("session_id", session_id),
        stage=state.get("stage", "kyc"),
        messages=state.get("messages", []),
        context=state.get("context", {}),
        meta=state.get("meta", {}),
    )

