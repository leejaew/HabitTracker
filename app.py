"""Application entry point.

This module does only two things:
  1. Provides the `create_app` factory that wires the layers together.
  2. Exposes a module-level `app` symbol so Gunicorn can serve `app:app`.

Keeping `app.py` thin makes it obvious where dependencies are constructed
and lets tests build a fresh app per test with a temp data file.
"""
from __future__ import annotations

import os
import secrets

from flask import Flask

from habit_tracker.repository import JsonHabitRepository
from habit_tracker.routes import create_blueprint
from habit_tracker.security import init_security
from habit_tracker.service import HabitService

DEFAULT_DATA_FILE = "habits.json"


def create_app(data_file: str = DEFAULT_DATA_FILE) -> Flask:
    """Build and configure a Flask app instance.

    The factory pattern lets us:
      - swap `data_file` for tests (point at a temp file),
      - construct multiple apps in the same process if ever needed,
      - keep all dependency wiring in one obvious place.
    """
    app = Flask(__name__)

    # Prefer an externally-provided secret in production so sessions and
    # CSRF tokens stay valid across restarts. Fall back to an ephemeral
    # key for local dev so the app still boots without configuration.
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

    init_security(app)

    # Compose the layers: repo -> service -> routes.
    repository = JsonHabitRepository(data_file)
    service = HabitService(repository)
    app.register_blueprint(create_blueprint(service))

    return app


# Gunicorn imports this symbol: `gunicorn ... app:app`
app = create_app()


if __name__ == "__main__":
    # Dev-only entry point. Production uses Gunicorn (see .replit
    # [deployment] section). debug=False because debug mode enables the
    # Werkzeug debugger which is a remote-code-execution risk if exposed.
    app.run(host="0.0.0.0", port=5000, debug=False)
