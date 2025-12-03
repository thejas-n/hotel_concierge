from __future__ import annotations

from google.adk.tools.function_tool import FunctionTool

from services.state_registry import get_current_manager


def _check_availability(party_size: int) -> dict:
    """
    Check for a free table that can seat the given party size.

    Returns table metadata if available, otherwise a message indicating no table is free.
    """
    manager = get_current_manager()
    table = manager.check_availability(party_size=party_size)
    if table:
        return {
            "available": True,
            "table": table.to_dict(),
            "note": "Table is free and can be assigned.",
        }
    return {
        "available": False,
        "table": None,
        "note": "No table currently free for this party size.",
    }


check_availability_tool = FunctionTool(_check_availability)
