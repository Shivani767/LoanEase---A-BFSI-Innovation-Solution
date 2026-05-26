from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import Request


class ConversationMemory:
    """In-memory conversation/session state store for AI chat flows."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str) -> Dict[str, Any]:
        """Return existing session state or create a new one."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "session_id": session_id,
                    "stage": "kyc",
                    "messages": [],
                    "context": {},
                    "meta": {},
                }
            return deepcopy(self._sessions[session_id])

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a chat message to session history."""
        with self._lock:
            session = self._sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "stage": "kyc",
                    "messages": [],
                    "context": {},
                    "meta": {},
                },
            )
            session["messages"].append({"role": role, "content": content})

    def set_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Merge context values into the session context."""
        with self._lock:
            session = self._sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "stage": "kyc",
                    "messages": [],
                    "context": {},
                    "meta": {},
                },
            )
            session["context"].update(context)

    def set_stage(self, session_id: str, stage: str) -> None:
        """Set current stage for the session."""
        with self._lock:
            session = self._sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "stage": "kyc",
                    "messages": [],
                    "context": {},
                    "meta": {},
                },
            )
            session["stage"] = stage

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Return message history for the session."""
        with self._lock:
            session = self._sessions.get(session_id, {})
            return deepcopy(session.get("messages", []))

    def has_session(self, session_id: str) -> bool:
        """Return True if session exists in memory."""
        with self._lock:
            return session_id in self._sessions

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return full session state for inspection, or None if missing."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            return deepcopy(session)

    def clear(self, session_id: str) -> bool:
        """Delete a session and return True if it existed."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


def get_memory(request: Request) -> ConversationMemory:
    """FastAPI dependency to access conversation memory from app state."""
    memory = request.app.state.memory
    if memory is None:
        raise RuntimeError("ConversationMemory not initialized")
    return memory
