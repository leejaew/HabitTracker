"""HTTP layer — Flask Blueprint that exposes the habit tracker as a REST API.

These handlers are intentionally thin. They:
  1. Parse the request,
  2. Delegate to the service,
  3. Translate domain exceptions into HTTP status codes.

No business logic lives here. That way the service can be tested without
spinning up Flask, and new transports (e.g. CLI, scheduled job) reuse the
same rules.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from flask_wtf.csrf import generate_csrf

from .service import (
    HabitAlreadyExists,
    HabitNotFound,
    HabitService,
)
from .validators import ValidationError


def create_blueprint(service: HabitService) -> Blueprint:
    """Build the blueprint with the service injected.

    A factory (rather than a module-level Blueprint) keeps the service
    dependency explicit and lets tests pass in a fake service.
    """
    bp = Blueprint("habits", __name__)

    # --- Pages -------------------------------------------------------------

    @bp.route("/", methods=["GET"])
    def index():
        # generate_csrf() both creates and rotates the per-session token,
        # making it available to the inline JS for the X-CSRFToken header.
        return render_template("index.html", csrf_token=generate_csrf())

    # --- API ---------------------------------------------------------------

    @bp.route("/api/habits", methods=["GET"])
    def list_habits():
        return jsonify({"habits": service.list_habits()})

    @bp.route("/api/habits", methods=["POST"])
    def add_habit():
        # Reject anything that isn't a JSON object outright (400). silent=True
        # prevents Flask from raising a default HTML error page on bad JSON.
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400
        try:
            service.add_habit(payload.get("name", ""))
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 422
        except HabitAlreadyExists as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"habits": service.list_habits()}), 201

    @bp.route("/api/habits/<path:name>", methods=["DELETE"])
    def remove_habit(name: str):
        try:
            service.remove_habit(name)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 422
        except HabitNotFound as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify({"habits": service.list_habits()})

    @bp.route("/api/habits/<path:name>/toggle", methods=["POST"])
    def toggle_habit(name: str):
        try:
            completed = service.toggle_today(name)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 422
        except HabitNotFound as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify({"completed": completed, "habits": service.list_habits()})

    return bp
