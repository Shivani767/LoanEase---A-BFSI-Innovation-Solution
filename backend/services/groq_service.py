from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional, Tuple

from fastapi import Depends, Request
from groq import AsyncGroq

logger = logging.getLogger("loanease.groq_service")


Message = Dict[str, str]


@dataclass
class GroqResult:
    """Container for Groq chat outputs."""

    text: str
    xai_trace: Dict[str, Any]
    model_used: str
    usage: Optional[Dict[str, Any]]


class GroqService:
    """Async Groq client wrapper with retry, fallback, and XAI trace parsing."""

    def __init__(
        self,
        api_key: str | None,
        primary_model: str = "llama-3.3-70b-versatile",
        fallback_model: str = "llama-3.1-8b-instant",
        timeout: int = 8,
    ) -> None:
        if not api_key:
            self._client = None
            self._connected = False
        else:
            try:
                self._client = AsyncGroq(api_key=api_key)
                self._connected = False
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
                self._client = None
                self._connected = False
        self._primary_model = primary_model
        self._fallback_model = fallback_model
        self._timeout = timeout
        self._last_model: Optional[str] = None
        self._fallback_used = False

    async def verify_connection(self) -> bool:
        """Verify Groq connectivity using a minimal test prompt."""
        if self._client is None:
            return False
        try:
            result = await self._chat_completion(
                model=self._primary_model,
                system_prompt="Respond with OK.",
                messages=[{"role": "user", "content": "ping"}],
                temperature=0.0,
                max_tokens=1,
            )
            self._connected = bool(result.text)
            self._last_model = result.model_used
            return self._connected
        except Exception as exc:
            logger.warning("Groq connectivity check failed: %s", exc)
            self._connected = False
            return False

    def status(self) -> Dict[str, Any]:
        """Return current Groq service status."""
        return {
            "connected": self._connected,
            "model": self._last_model,
            "fallback_used": self._fallback_used,
        }

    async def chat(
        self,
        system_prompt: str,
        messages: List[Message],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a full response and return clean text plus XAI trace."""
        from core.config import settings
        from core.fallback_map import get_fallback

        if self._client is None or not self._connected:
            if settings.DEMO_MODE:
                fallback = get_fallback("groq")
                return fallback["text"], fallback["trace"]
            
            # Fallback response when Groq is not available
            fallback_response = "I'm sorry, I'm currently unable to process your request. Please try again later."
            return fallback_response, {"error": "Groq client not initialized", "fallback_used": True}
        
        try:
            result = await self._chat_completion(
                model=self._primary_model,
                system_prompt=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return result.text, result.xai_trace
        except Exception as e:
            if settings.DEMO_MODE:
                logger.error(f"Groq Chat failed, using demo fallback: {e}")
                fallback = get_fallback("groq")
                return fallback["text"], fallback["trace"]
            raise e

    async def stream_chat(
        self,
        system_prompt: str,
        messages: List[Message],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream response text chunks, then emit XAI trace payload."""
        model = self._primary_model
        attempts = 0
        buffer = ""
        trace_payload: Dict[str, Any] = {}
        seen_trace_marker = False

        while attempts < 3:
            attempts += 1
            try:
                stream = await self._client.chat.completions.create(
                    model=model,
                    messages=self._build_messages(system_prompt, messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                logger.debug("Groq stream model=%s attempt=%s", model, attempts)

                async for chunk in stream:
                    delta = ""
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta.get("content") or ""
                    if not delta:
                        continue

                    buffer += delta
                    if not seen_trace_marker and "<!-- xai_trace:" in buffer:
                        seen_trace_marker = True

                    if not seen_trace_marker:
                        yield delta

                clean_text, trace_payload = self._extract_xai_trace(buffer)
                if clean_text and seen_trace_marker:
                    # If we stopped streaming due to the marker, emit any leftover clean text.
                    yield clean_text

                self._connected = True
                self._last_model = model
                self._fallback_used = model != self._primary_model
                break
            except Exception as exc:
                status = _get_status_code(exc)
                logger.warning("Groq stream error on attempt %s: %s", attempts, exc)
                if status == 429:
                    await _backoff(attempts)
                    continue
                if status and status >= 500:
                    model = self._fallback_model
                    await _backoff(attempts)
                    continue
                raise

        yield f"XAI_TRACE::{json.dumps(trace_payload)}"

    async def route_intent(
        self,
        system_prompt: str,
        messages: List[Message],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Classify intent using a fast Groq model and return JSON-only payload."""
        result = await self._chat_completion(
            model=self._fallback_model,
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _safe_json_parse(result.text)

    async def _chat_completion(
        self,
        model: str,
        system_prompt: str,
        messages: List[Message],
        temperature: float,
        max_tokens: int,
    ) -> GroqResult:
        """Internal helper for non-streaming chat completion with retry/fallback."""
        attempts = 0
        fallback_model = self._fallback_model
        selected_model = model

        while attempts < 3:
            attempts += 1
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=selected_model,
                        messages=self._build_messages(system_prompt, messages),
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=self._timeout,
                )
                usage = getattr(response, "usage", None)
                usage_dict = usage.model_dump() if usage else None
                logger.debug(
                    "Groq response model=%s attempt=%s usage=%s",
                    selected_model,
                    attempts,
                    usage_dict,
                )

                content = response.choices[0].message.content if response.choices else ""
                clean_text, trace = self._extract_xai_trace(content or "")

                self._connected = True
                self._last_model = selected_model
                self._fallback_used = selected_model != self._primary_model

                return GroqResult(
                    text=clean_text,
                    xai_trace=trace,
                    model_used=selected_model,
                    usage=usage_dict,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Groq timeout model=%s attempt=%s (limit=%ss)",
                    selected_model, attempts, self._timeout,
                )
                if attempts < 3:
                    selected_model = fallback_model
                    continue
                raise RuntimeError(f"Groq request timed out after {self._timeout}s")
            except Exception as exc:
                status = _get_status_code(exc)
                logger.warning("Groq error model=%s attempt=%s: %s", selected_model, attempts, exc)
                if status == 429:
                    await _backoff(attempts)
                    continue
                if status and status >= 500:
                    selected_model = fallback_model
                    await _backoff(attempts)
                    continue
                raise

    def _build_messages(self, system_prompt: str, messages: Iterable[Message]) -> List[Message]:
        return [{"role": "system", "content": system_prompt}, *list(messages)]

    def _extract_xai_trace(self, content: str) -> Tuple[str, Dict[str, Any]]:
        match = re.search(r"<!--\s*xai_trace:\s*(\{.*?\})\s*-->", content, flags=re.DOTALL)
        trace: Dict[str, Any] = {}
        if match:
            trace = _safe_json_parse(match.group(1))
        cleaned = re.sub(r"<!--\s*xai_trace:.*?-->", "", content, flags=re.DOTALL).strip()
        return cleaned, trace


def get_groq_service(request: Request) -> GroqService:
    """FastAPI dependency to access GroqService from app state."""
    service = request.app.state.groq_service
    if service is None:
        raise RuntimeError("GroqService not initialized")
    return service


def _get_status_code(exc: Exception) -> Optional[int]:
    return getattr(exc, "status_code", None) or getattr(exc, "status", None)


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))


def _safe_json_parse(payload: str) -> Dict[str, Any]:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}
