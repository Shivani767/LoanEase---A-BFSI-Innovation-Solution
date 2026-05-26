from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class ConversationMemory:
    """Redis-backed conversation store with in-process fallback."""

    _CHAT_TTL_SECONDS = 24 * 60 * 60
    _MAX_MESSAGES = 24

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        # Local fallback storage (dev mode when Redis is unavailable).
        self._local: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _chat_key(session_id: str) -> str:
        return f"chat:{session_id}"

    @staticmethod
    def _stage_key(session_id: str) -> str:
        return f"stage:{session_id}"

    @staticmethod
    def _ctx_key(session_id: str) -> str:
        return f"ctx:{session_id}"

    def _local_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._local:
            self._local[session_id] = {
                "chat": [],
                "stage": "kyc",
                "ctx": {},
            }
        return self._local[session_id]

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        if self._redis is None:
            session = self._local_session(session_id)
            return list(session["chat"])

        raw_messages = await self._redis.lrange(self._chat_key(session_id), 0, -1)
        history: List[Dict[str, Any]] = []
        for item in raw_messages or []:
            try:
                payload = item.decode("utf-8") if isinstance(item, bytes) else str(item)
                decoded = json.loads(payload)
                if isinstance(decoded, dict):
                    history.append(decoded)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return history

    async def append(self, session_id: str, role: str, content: str) -> None:
        message = {"role": role, "content": content}

        if self._redis is None:
            session = self._local_session(session_id)
            session["chat"].append(message)
            # Keep only last 24 messages in fallback mode.
            session["chat"] = session["chat"][-self._MAX_MESSAGES :]
            return

        key = self._chat_key(session_id)
        serialized = json.dumps(message, ensure_ascii=False)
        async with self._redis.pipeline(transaction=True) as pipe:
            # Push, trim to last N, and set TTL in one round trip.
            pipe.rpush(key, serialized)
            pipe.ltrim(key, -self._MAX_MESSAGES, -1)
            pipe.expire(key, self._CHAT_TTL_SECONDS)
            await pipe.execute()

    async def get_stage(self, session_id: str) -> str:
        if self._redis is None:
            session = self._local_session(session_id)
            return str(session.get("stage", "kyc"))

        value = await self._redis.get(self._stage_key(session_id))
        if value is None:
            return "kyc"
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return "kyc"
        return str(value)

    async def set_stage(self, session_id: str, stage: str) -> None:
        normalized = (stage or "kyc").strip().lower() or "kyc"

        if self._redis is None:
            session = self._local_session(session_id)
            session["stage"] = normalized
            return

        key = self._stage_key(session_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(key, normalized)
            pipe.expire(key, self._CHAT_TTL_SECONDS)
            await pipe.execute()

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        if self._redis is None:
            session = self._local_session(session_id)
            ctx = session.get("ctx", {})
            return dict(ctx) if isinstance(ctx, dict) else {}

        raw = await self._redis.get(self._ctx_key(session_id))
        if raw is None:
            return {}
        payload = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    async def update_context(self, session_id: str, updates: Dict[str, Any]) -> None:
        safe_updates = updates if isinstance(updates, dict) else {}

        if self._redis is None:
            session = self._local_session(session_id)
            existing = session.get("ctx", {})
            merged: Dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
            merged.update(safe_updates)
            session["ctx"] = merged
            return

        key = self._ctx_key(session_id)
        existing_raw = await self._redis.get(key)
        existing_ctx: Dict[str, Any] = {}
        if existing_raw is not None:
            payload = existing_raw.decode("utf-8") if isinstance(existing_raw, bytes) else str(existing_raw)
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, dict):
                    existing_ctx = decoded
            except json.JSONDecodeError:
                existing_ctx = {}

        existing_ctx.update(safe_updates)

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(key, json.dumps(existing_ctx, ensure_ascii=False))
            pipe.expire(key, self._CHAT_TTL_SECONDS)
            await pipe.execute()

    async def clear(self, session_id: str) -> None:
        if self._redis is None:
            self._local.pop(session_id, None)
            return

        await self._redis.delete(
            self._chat_key(session_id),
            self._stage_key(session_id),
            self._ctx_key(session_id),
        )

