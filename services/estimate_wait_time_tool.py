from __future__ import annotations

from google.adk.tools.function_tool import FunctionTool

from services.state_registry import get_current_manager


def _estimate_wait_time(party_size: int) -> dict:
    manager = get_current_manager()
    eta = manager.estimate_wait_time(party_size=party_size)
    return {
        "party_size": party_size,
        "eta_minutes": eta,
        "note": "Estimated minutes until a suitable table is free" if eta is not None else "No suitable table predicted yet",
    }


estimate_wait_time_tool = FunctionTool(_estimate_wait_time)
