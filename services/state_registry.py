from __future__ import annotations

import contextvars
from typing import Dict

from services.hotel import HotelManager


_managers: Dict[str, HotelManager] = {}
_current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_session_id", default=None
)


def ensure_manager(session_id: str) -> HotelManager:
    """Get or create a HotelManager for the session."""
    if session_id not in _managers:
        _managers[session_id] = HotelManager()
    return _managers[session_id]


def get_manager(session_id: str) -> HotelManager:
    return ensure_manager(session_id)


def set_current_session(session_id: str) -> None:
    _current_session_id.set(session_id)


def get_current_manager() -> HotelManager:
    session_id = _current_session_id.get()
    if not session_id:
        # Fallback to a shared manager if no session context is set.
        return ensure_manager("__default__")
    return ensure_manager(session_id)
