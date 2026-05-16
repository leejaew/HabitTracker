"""Input validation for user-supplied data.

Kept as a tiny module (not a class) because the rules are stateless.
If validation grows complex (multi-field forms, conditional rules),
promote this to a class or move to Flask-WTF Form objects.
"""
from __future__ import annotations

import re

HABIT_NAME_MAX_LEN = 60

# Allow letters/digits/underscore (\w), spaces, and a small set of common
# punctuation. Deliberately restrictive — it's much easier to widen this
# later than to deal with a stored XSS payload that slipped through.
_HABIT_NAME_PATTERN = re.compile(r"^[\w\s\-',\.!?()&]+$", re.UNICODE)


class ValidationError(ValueError):
    """Raised when user input fails validation.

    Subclasses ValueError so callers that want generic handling still work,
    but the dedicated type lets the HTTP layer map cleanly to a 422 status.
    """


def clean_habit_name(name: object) -> str:
    """Validate and normalize a habit name.

    Returns the trimmed name on success, raises `ValidationError` otherwise.
    Centralizing this means the CLI and the web layer reject the same set
    of inputs — no duplicate rule lists to drift apart.
    """
    if not isinstance(name, str):
        raise ValidationError("Habit name must be text.")
    trimmed = name.strip()
    if not trimmed:
        raise ValidationError("Habit name cannot be empty.")
    if len(trimmed) > HABIT_NAME_MAX_LEN:
        raise ValidationError(
            f"Habit name must be {HABIT_NAME_MAX_LEN} characters or fewer."
        )
    if not _HABIT_NAME_PATTERN.match(trimmed):
        raise ValidationError("Habit name contains invalid characters.")
    return trimmed
