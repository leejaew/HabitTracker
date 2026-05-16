"""Domain layer — pure entities and rules.

This module has no dependencies on Flask, files, or any framework.
That keeps it trivially testable and means changes to storage or
transport never ripple in here.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Optional


class Habit:
    """A single habit and its day-by-day completion history.

    `history` maps an ISO date string ("YYYY-MM-DD") -> bool.
    We store dates as strings so the entity serializes to JSON cleanly
    without a custom encoder. The conversion stays at this boundary;
    callers always work with `date` objects.
    """

    __slots__ = ("name", "history")  # tiny memory win + catches typos early

    def __init__(self, name: str, history: Optional[Dict[str, bool]] = None) -> None:
        self.name: str = name
        # Defensive copy so the caller can't mutate our internal state
        # by holding a reference to the dict they passed in.
        self.history: Dict[str, bool] = dict(history) if history else {}

    # --- Mutators ----------------------------------------------------------
    # These are intentionally tiny — the service layer decides *when* to
    # call them; the entity only knows *how* to apply the change.

    def mark(self, completed: bool, on: Optional[date] = None) -> None:
        """Record completion (or non-completion) for the given day."""
        day = on or date.today()
        self.history[day.isoformat()] = bool(completed)

    # --- Queries -----------------------------------------------------------

    def is_complete(self, on: Optional[date] = None) -> bool:
        day = on or date.today()
        return self.history.get(day.isoformat(), False)

    def streak(self, today: Optional[date] = None) -> int:
        """Count consecutive completed days ending at `today`.

        `today` is a parameter (not just `date.today()`) so tests can pin
        a specific day without monkey-patching the clock.
        """
        cursor = today or date.today()
        count = 0
        while self.history.get(cursor.isoformat(), False):
            count += 1
            cursor -= timedelta(days=1)
        return count

    # --- Serialization -----------------------------------------------------

    def to_view(self, today: Optional[date] = None) -> dict:
        """Shape the entity for the API/UI.

        Kept separate from raw storage shape so the wire format can evolve
        (e.g. add `last_completed`) without touching the persisted JSON.
        """
        day = today or date.today()
        return {
            "name": self.name,
            "streak": self.streak(day),
            "completed_today": self.is_complete(day),
        }
