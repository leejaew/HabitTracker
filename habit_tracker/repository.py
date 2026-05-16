"""Persistence layer.

We define an abstract `HabitRepository` and one concrete `JsonHabitRepository`.
The abstraction exists for one concrete reason: storage is the most likely
thing to change (JSON file -> SQLite -> Postgres as the app grows, especially
because autoscale deployments have an ephemeral filesystem). Defining the
boundary now means future swaps don't touch the service or routes.

We do *not* abstract anything else (no UnitOfWork, no Specification pattern)
because there's no second implementation in sight — speculative abstractions
are the textbook example of over-engineering.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

from .domain import Habit


class HabitRepository(ABC):
    """Storage interface. Implementations decide how habits are persisted."""

    @abstractmethod
    def list(self) -> List[Habit]: ...

    @abstractmethod
    def get(self, name: str) -> Optional[Habit]: ...

    @abstractmethod
    def save(self, habit: Habit) -> None: ...

    @abstractmethod
    def delete(self, name: str) -> bool: ...

    @abstractmethod
    def update(self, name: str, mutator: Callable[[Habit], None]) -> Optional[Habit]:
        """Atomically apply `mutator(habit)` and persist the result.

        Returns the mutated habit, or None if no habit exists with that name.
        This is the only safe way to perform a read-modify-write — `get` +
        `save` from the service layer would race under concurrent requests.
        """


class JsonHabitRepository(HabitRepository):
    """File-backed repository using a JSON document.

    Design choices and trade-offs:

    1. In-memory cache. We load the file once on construction and keep the
       habits in a dict, so reads are O(1) and don't hit disk. Every write
       persists the whole document — fine for the dataset sizes a habit
       tracker realistically has (tens of habits, not millions).

    2. Thread safety. Gunicorn's default sync workers handle one request
       at a time per worker, but we still take a lock so this class is
       safe under threaded workers or in tests. The lock is cheap when
       uncontended.

    3. Atomic writes. We write to a temp file and `os.replace` it into
       place. That prevents a half-written `habits.json` if the process
       is killed mid-write (e.g. autoscale instance shutdown).

    4. Caveat for autoscale. The local filesystem is *ephemeral* and not
       shared between instances. State will not persist across cold starts
       or scale-outs. The right long-term fix is a real database; that
       swap is one new repository implementation away thanks to the ABC.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._habits: Dict[str, Habit] = {}
        self._load()

    # --- Reads -------------------------------------------------------------

    def list(self) -> List[Habit]:
        # Return a snapshot list, not a view, so callers iterating outside
        # the lock can't see mid-mutation state.
        with self._lock:
            return list(self._habits.values())

    def get(self, name: str) -> Optional[Habit]:
        with self._lock:
            return self._habits.get(name)

    # --- Writes ------------------------------------------------------------

    def save(self, habit: Habit) -> None:
        """Upsert a habit and flush to disk."""
        with self._lock:
            self._habits[habit.name] = habit
            self._flush()

    def delete(self, name: str) -> bool:
        """Remove a habit. Returns True if it existed, False otherwise."""
        with self._lock:
            if name not in self._habits:
                return False
            del self._habits[name]
            self._flush()
            return True

    def update(self, name, mutator):
        """Read-modify-write under a single lock — no torn updates possible."""
        with self._lock:
            habit = self._habits.get(name)
            if habit is None:
                return None
            mutator(habit)
            self._flush()
            return habit

    # --- Internals ---------------------------------------------------------

    def _load(self) -> None:
        """Read the JSON file into memory. Tolerates missing/corrupt files.

        On corruption we start empty rather than crash — the operator can
        inspect the file. We do not silently rename or delete user data.
        """
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        if not isinstance(raw, dict):
            return

        for name, history in raw.items():
            if not isinstance(name, str) or not isinstance(history, dict):
                continue
            # Coerce values to bool so a tampered file can't smuggle in
            # arbitrary types that break downstream code.
            clean_history = {
                str(k): bool(v) for k, v in history.items() if isinstance(k, str)
            }
            self._habits[name] = Habit(name, clean_history)

    def _flush(self) -> None:
        """Atomically persist the current state to disk."""
        data = {name: h.history for name, h in self._habits.items()}
        directory = os.path.dirname(os.path.abspath(self._path)) or "."
        # NamedTemporaryFile keeps the temp file in the same directory as
        # the target so `os.replace` is atomic (same filesystem).
        with tempfile.NamedTemporaryFile(
            "w", dir=directory, delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name
        os.replace(tmp_path, self._path)
