"""Application service — the single entry point for business operations.

Every state change funnels through `HabitService`. Routes and the CLI both
call methods here; neither touches the repository or the domain directly.
That gives us one place to enforce rules (validation, "already exists",
"not found") and one place to add cross-cutting concerns later (auditing,
events, rate limiting per habit, etc.) without rewriting callers.
"""
from __future__ import annotations

from typing import List

from .domain import Habit
from .repository import HabitRepository
from .validators import clean_habit_name


class HabitNotFound(LookupError):
    """The requested habit does not exist."""


class HabitAlreadyExists(ValueError):
    """A habit with the requested name is already tracked."""


class HabitService:
    """Coordinates the domain and the repository.

    Constructor injection (rather than module-level singletons) keeps this
    testable and lets the app factory wire whatever repository
    implementation it likes.
    """

    def __init__(self, repository: HabitRepository) -> None:
        self._repo = repository

    # --- Queries -----------------------------------------------------------

    def list_habits(self) -> List[dict]:
        """Return all habits in their wire format, suitable for jsonify()."""
        return [h.to_view() for h in self._repo.list()]

    # --- Commands ----------------------------------------------------------

    def add_habit(self, name: str) -> Habit:
        """Create a new habit. Raises on bad input or duplicate."""
        clean = clean_habit_name(name)
        if self._repo.get(clean) is not None:
            raise HabitAlreadyExists(f"Habit '{clean}' already exists.")
        habit = Habit(clean)
        self._repo.save(habit)
        return habit

    def remove_habit(self, name: str) -> None:
        """Delete a habit and all its history. Raises if absent."""
        clean = clean_habit_name(name)
        if not self._repo.delete(clean):
            raise HabitNotFound(f"Habit '{clean}' not found.")

    def toggle_today(self, name: str) -> bool:
        """Flip today's completion state. Returns the *new* state.

        Toggle (vs. explicit complete/incomplete) matches the UI's single
        checkbox affordance and avoids a round-trip just to read state.

        We delegate the read-modify-write to `repository.update` so the
        flip happens under a single lock. Doing `get` then `save` here
        would race: two concurrent toggles could read the same state and
        both write the same result, silently losing one user's click.
        """
        clean = clean_habit_name(name)
        new_state: dict = {}  # nonlocal-style capture without `nonlocal`

        def _flip(habit: Habit) -> None:
            state = not habit.is_complete()
            habit.mark(state)
            new_state["value"] = state

        habit = self._repo.update(clean, _flip)
        if habit is None:
            raise HabitNotFound(f"Habit '{clean}' not found.")
        return new_state["value"]
