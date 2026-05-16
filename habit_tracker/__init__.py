"""Habit Tracker package.

Layered architecture (inside-out):

    domain      -> Pure entities and rules. No I/O, no framework.
    repository  -> Persistence abstraction + concrete JSON implementation.
    service     -> Business operations. Orchestrates domain + repository.
                   The CLI and the web routes both depend on this.
    routes      -> HTTP layer. Translates requests to service calls.
    security    -> Cross-cutting: CSRF + security headers.

Why this split for a small app?
    - The repository boundary makes it trivial to swap JSON for a real
      database later (the most likely future change).
    - The service boundary lets the CLI (main.py) and the web app share
      the exact same business rules — one source of truth.
    - Everything else is kept flat. We deliberately avoid DI containers,
      DTO classes, and abstract factories to prevent over-engineering.
"""
