from __future__ import annotations

from google.adk.tools.function_tool import FunctionTool

from services.state_registry import get_current_manager


def _update_reservation(
    scope: str,
    name: str,
    party_size: int,
    table_id: str,
) -> dict:
    """
    Update an existing reservation or waitlist entry.

    scope: "table" or "waitlist"
    name: guest name
    party_size: new party size (also used to confirm identity)
    table_id: required when scope="table"
    """
    manager = get_current_manager()
    if scope == "table":
        if not table_id:
            return {"success": False, "message": "table_id is required for table updates."}
        return manager.update_table_assignment(table_id=table_id, guest_name=name)

    if scope == "waitlist":
        return manager.update_waitlist_entry(name=name, party_size=party_size)

    return {"success": False, "message": "Invalid scope. Use 'table' or 'waitlist'."}


update_reservation_tool = FunctionTool(_update_reservation)
