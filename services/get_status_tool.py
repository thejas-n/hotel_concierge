from __future__ import annotations

from google.adk.tools.function_tool import FunctionTool

from services.state_registry import get_current_manager


def _get_status() -> dict:
    """
    Return current table status and waitlist with ETAs.
    """
    manager = get_current_manager()
    return manager.get_status()


get_status_tool = FunctionTool(_get_status)
