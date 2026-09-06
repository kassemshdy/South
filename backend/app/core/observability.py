"""Error tracking.

Inert unless ``SENTRY_DSN`` is set, so a developer's tracebacks never leave
their machine and the test suite never talks to the network.

This service handles things that must not end up in a third-party error
report: owner login phone numbers, OTP codes, and identity documents. Sentry's
default PII collection is therefore off rather than scrubbed after the fact,
and :func:`_scrub` strips the few fields that can still reach an event through
a URL or a logged extra — matching the stance the frontend SDK takes in
``frontend/src/main.tsx``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.config import Settings

if TYPE_CHECKING:
    from sentry_sdk.types import Event, Hint

logger = logging.getLogger(__name__)

# Field names that carry a secret or a personal identifier anywhere they
# appear. Matched case-insensitively against keys, not values, so a business's
# *public* phone number in a listing payload is unaffected — only the request
# fields that carry an owner's own credentials are removed.
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "code",
        "cookie",
        "otp",
        "otp_code",
        "password",
        "personal_phone_number",
        "phone_number",
        "secret_key",
        "set-cookie",
        "token",
        "access_token",
    }
)

REDACTED = "[redacted]"


def _scrub(value: Any) -> Any:
    """Recursively redact sensitive keys in an event payload."""
    if isinstance(value, dict):
        return {
            key: REDACTED if str(key).lower() in SENSITIVE_KEYS else _scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def _before_send(event: Event, _hint: Hint) -> Event:
    # The query string is a flat string rather than a mapping, so it survives
    # the key-based scrub above; a phone number in ?q= would otherwise ship.
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("query_string", None)
        request.pop("data", None)
    scrubbed: Event = _scrub(event)
    return scrubbed


def configure_error_tracking(settings: Settings) -> None:
    """Initialise Sentry when a DSN is configured; otherwise do nothing."""
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - the dependency is in requirements
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.sentry_release,
        # Never attach request bodies, headers, cookies or the client IP.
        send_default_pii=False,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        before_send=_before_send,
    )
    logger.info("Error tracking enabled", extra={"env": settings.app_env})
