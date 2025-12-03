from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import datetime


@dataclass
class Table:
    table_id: str
    seats: int
    table_type: str
    status: str = "free"
    guest_name: Optional[str] = None
    assigned_time: Optional[datetime.datetime] = None # New attribute

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.table_id,
            "seats": self.seats,
            "type": self.table_type,
            "status": self.status,
            "guest_name": self.guest_name,
            "assigned_time": self.assigned_time.isoformat() if self.assigned_time else None,
        }


@dataclass
class WaitlistEntry:
    name: str
    party_size: int


@dataclass
class HotelManager:
    tables: List[Table] = field(default_factory=list)
    waitlist: List[WaitlistEntry] = field(default_factory=list)
    last_event: Optional[Dict[str, Any]] = None
    default_dining_duration_minutes: int = 50 # New configurable attribute

    def __post_init__(self) -> None:
        if self.tables:
            return
        # Bar seats
        for i in range(5):
            self.tables.append(Table(f"BAR-{i+1}", 1, "bar"))
        # 2,4,6 seaters
        for prefix, count, seats in (("T2", 5, 2), ("T4", 5, 4), ("T6", 1, 6)):
            for i in range(count):
                self.tables.append(Table(f"{prefix}-{i+1}", seats, "standard"))

    # --- Helpers -----------------------------------------------------------------
    def _find_table(self, table_id: str) -> Optional[Table]:
        return next((t for t in self.tables if t.table_id == table_id), None)

    def _record_event(self, event: Dict[str, Any]) -> None:
        self.last_event = event

    def consume_event(self) -> Optional[Dict[str, Any]]:
        event, self.last_event = self.last_event, None
        return event
    
    def _calculate_table_eta(self, table: Table) -> int:
        if table.status != "occupied" or not table.assigned_time:
            return 0 # Not applicable
        
        elapsed_time = (datetime.datetime.now() - table.assigned_time).total_seconds() / 60
        remaining_time = max(0, self.default_dining_duration_minutes - int(elapsed_time))
        return remaining_time

    # --- Public API ---------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        current_time = datetime.datetime.now()

        # Create a mutable copy of tables for simulation
        simulated_tables = []
        for t in self.tables:
            sim_table_dict = t.to_dict()
            sim_table_dict["estimated_free_time"] = current_time # For currently free tables
            if t.status == "occupied" and t.assigned_time:
                time_to_free = self._calculate_table_eta(t)
                sim_table_dict["estimated_free_time"] = t.assigned_time + datetime.timedelta(minutes=self.default_dining_duration_minutes)
            simulated_tables.append(sim_table_dict)

        # Sort simulated tables by estimated_free_time
        simulated_tables.sort(key=lambda x: x["estimated_free_time"])

        tables_data = []
        for t in self.tables:
            table_dict = t.to_dict()
            if t.status == "occupied":
                table_dict["eta_minutes"] = self._calculate_table_eta(t)
            tables_data.append(table_dict)

        waitlist_data = []
        # Simulate waitlist seating to calculate accurate ETAs
        for entry in self.waitlist:
            entry_dict = entry.__dict__
            found_table = False
            
            # Find the earliest available table in the simulation for this party
            for sim_table in simulated_tables:
                if sim_table["seats"] >= entry.party_size:
                    # Calculate wait time based on when this table is next free
                    wait_until_free = max(0, int((sim_table["estimated_free_time"] - current_time).total_seconds() / 60))
                    entry_dict["eta_minutes"] = wait_until_free
                    
                    # Update the simulated table's free time to account for this party's dining duration
                    sim_table["estimated_free_time"] += datetime.timedelta(minutes=self.default_dining_duration_minutes)
                    found_table = True
                    break
            
            if not found_table:
                entry_dict["eta_minutes"] = None # No suitable table found even in simulation
            waitlist_data.append(entry_dict)

        latest_event = self.consume_event()

        return {
            "tables": tables_data,
            "waitlist": waitlist_data,
            "last_event": latest_event,
        }

    def check_availability(self, party_size: int) -> Optional[Table]:
        return next(
            (t for t in self.tables if t.status == "free" and t.seats >= party_size),
            None,
        )

    def assign_table(self, table: Table, guest_name: str) -> str:
        table.status = "occupied"
        table.guest_name = guest_name
        table.assigned_time = datetime.datetime.now() # Set assigned time
        self._record_event(
            {
                "type": "table_assigned",
                "table": table.table_id,
                "name": guest_name,
                "party_size": table.seats,
            }
        )
        return table.table_id

    def add_to_waitlist(self, name: str, party_size: int) -> int:
        self.waitlist.append(WaitlistEntry(name=name, party_size=party_size))
        position = len(self.waitlist)
        self._record_event(
            {
                "type": "waitlist",
                "name": name,
                "party_size": party_size,
                "position": position,
            }
        )
        return position

    def checkout_and_fill_waitlist(self, table_id: str) -> Dict[str, Any]:
        table = self._find_table(table_id)
        if not table:
            return {"success": False, "message": "Table not found."}

        previous_guest = table.guest_name
        table.status = "free"
        table.guest_name = None
        table.assigned_time = None # Reset assigned time on checkout

        assigned_guest: Optional[WaitlistEntry] = None
        for idx, entry in enumerate(list(self.waitlist)):
            if entry.party_size <= table.seats:
                assigned_guest = self.waitlist.pop(idx)
                table.status = "occupied"
                table.guest_name = assigned_guest.name
                table.assigned_time = datetime.datetime.now() # Set assigned time for new assignment
                break

        result: Dict[str, Any] = {
            "success": True,
            "table": table.table_id,
            "cleared_guest": previous_guest,
            "assigned_guest": assigned_guest.__dict__ if assigned_guest else None,
        }

        if assigned_guest:
            self._record_event(
                {
                    "type": "table_assigned",
                    "table": table.table_id,
                    "name": assigned_guest.name,
                    "party_size": assigned_guest.party_size,
                }
            )
            result["announcement"] = (
                f"Party for {assigned_guest.name}, party of {assigned_guest.party_size}, your table {table.table_id} is ready!"
            )

        return result

    def update_table_assignment(self, table_id: str, guest_name: str) -> Dict[str, Any]:
        table = self._find_table(table_id)
        if not table:
            return {"success": False, "message": "Table not found."}
        if table.status != "occupied":
            return {"success": False, "message": "Table is not currently occupied."}
        table.guest_name = guest_name
        table.assigned_time = datetime.datetime.now()
        return {"success": True, "table": table.to_dict(), "message": f"Updated table {table_id} for {guest_name}."}

    def update_waitlist_entry(self, name: str, party_size: int) -> Dict[str, Any]:
        for entry in self.waitlist:
            if entry.name.lower() == name.lower():
                entry.party_size = party_size
                return {"success": True, "entry": entry.__dict__, "message": f"Updated waitlist for {name} to party size {party_size}."}
        return {"success": False, "message": "Waitlist entry not found."}
