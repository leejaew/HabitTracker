"""Command-line interface for the habit tracker.

Kept as a separate transport on top of the same service layer used by the
web app. The CLI exists because:
  - It's how the project originally shipped, and
  - It's a working demonstration that the service layer is reusable —
    no business logic is duplicated between the CLI and the HTTP routes.
"""
from __future__ import annotations

from habit_tracker.repository import JsonHabitRepository
from habit_tracker.service import (
    HabitAlreadyExists,
    HabitNotFound,
    HabitService,
)
from habit_tracker.validators import ValidationError

DATA_FILE = "habits.json"


def main() -> None:
    # Same composition as create_app(), minus Flask. Two transports, one core.
    service = HabitService(JsonHabitRepository(DATA_FILE))

    actions = {
        "1": ("Add a new habit", _add),
        "2": ("Remove a habit", _remove),
        "3": ("Toggle today's completion", _toggle),
        "4": ("View all habits", _view),
        "5": ("Quit", None),
    }

    while True:
        print("\nHabit Tracker")
        for key, (label, _) in actions.items():
            print(f"  {key}. {label}")
        choice = input("Choose: ").strip()

        if choice == "5":
            print("Goodbye!")
            return

        entry = actions.get(choice)
        if entry is None:
            print("Invalid choice.")
            continue

        try:
            entry[1](service)
        except (ValidationError, HabitNotFound, HabitAlreadyExists) as exc:
            # All expected, user-facing errors share one display path so
            # the menu never crashes on bad input.
            print(f"Error: {exc}")


# --- Action handlers -------------------------------------------------------
# Each takes the service so they can be tested independently of input().

def _add(service: HabitService) -> None:
    name = input("Habit name: ")
    service.add_habit(name)
    print("Added.")


def _remove(service: HabitService) -> None:
    name = input("Habit name: ")
    service.remove_habit(name)
    print("Removed.")


def _toggle(service: HabitService) -> None:
    name = input("Habit name: ")
    state = service.toggle_today(name)
    print("Marked complete." if state else "Marked incomplete.")


def _view(service: HabitService) -> None:
    habits = service.list_habits()
    if not habits:
        print("No habits yet.")
        return
    for h in habits:
        mark = "[x]" if h["completed_today"] else "[ ]"
        print(f"  {mark} {h['name']}  (streak: {h['streak']})")


if __name__ == "__main__":
    main()
