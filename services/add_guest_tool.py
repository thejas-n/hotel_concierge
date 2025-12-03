from __future__ import annotations

from typing import Optional

from google.adk.tools.function_tool import FunctionTool

from services.state_registry import get_current_manager


def _add_guest(
    name: str,
    party_size: int,
    action: str = "auto",
    table_id: Optional[str] = None,
) -> dict:
    """
    Add a guest party. Assigns a table if available; otherwise places on waitlist.

    Parameters:
    - name: guest name.
    - party_size: number of guests.
    - action: "auto" (default), "check_in", or "waitlist".
    - table_id: optional specific table to check-in to.
    """
    manager = get_current_manager()
    chosen_table = None

    # If a table_id is provided and action is check_in, try to use that table first.
    if action == "check_in" and table_id:
        chosen_table = manager._find_table(table_id)
        if not chosen_table or chosen_table.status != "free":
            chosen_table = None  # fall back to availability check

    if not chosen_table:
        chosen_table = manager.check_availability(party_size=party_size)

    if chosen_table and action != "waitlist":
        assigned_table = manager.assign_table(table=chosen_table, guest_name=name)
        return {
            "assigned": True,
            "table": assigned_table,
            "waitlist_position": None,
            "message": f"Seated {name} at {assigned_table}.",
            "status": "seated",
        }

    position = manager.add_to_waitlist(name=name, party_size=party_size)
    return {
        "assigned": False,
        "table": None,
        "waitlist_position": position,
        "message": f"No table free; added to waitlist at position {position}.",
        "status": "waitlisted",
    }


add_guest_tool = FunctionTool(_add_guest)
