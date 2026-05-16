"""Cross-cutting security setup: CSRF + response headers.

Pulled out of the route module so the HTTP handlers stay focused on
request/response shaping. Centralizing headers also means there's one
place to audit when a CSP needs to change.
"""
from __future__ import annotations

from flask import Flask
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

# Locked-down CSP. We allow:
#   - self for everything by default
#   - Google Fonts stylesheet + font files
#   - inline styles (the page ships its own <style> block)
#   - inline scripts (single small bootstrap script in the template)
#   - data: URIs for images (the SVG favicon)
# If you add a CDN later, extend the relevant directive here only.
_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "script-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:;"
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": _CSP,
}


def init_security(app: Flask) -> None:
    """Wire CSRF protection and apply security headers to every response."""
    csrf.init_app(app)

    @app.after_request
    def _apply_headers(response):
        # setdefault avoids clobbering anything a handler set deliberately.
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
