"""Human verification on the public registration forms.

Cloudflare Turnstile, verified server-side: the browser widget produces a token
and this module asks Cloudflare whether it is genuine. A token the client
reports as valid means nothing on its own — the check that counts is this one.

**Inert without its secret**, like every optional integration here. With
``TURNSTILE_SECRET_KEY`` unset there is no verification call and nothing is
rejected, so local development and the test suite never touch the network and a
developer never needs a Cloudflare account to run the app. That is the same rule
AGENTS.md states for Sentry, analytics and the social links, and it is the
reason this returns rather than raises when unconfigured.

A configured secret is the opposite: a token that fails, or a verification call
that cannot be made, refuses the submission. An outage at Cloudflare closing the
registration form is the safer failure — the alternative is a form that silently
stops being protected exactly when someone is attacking it.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.core.errors import ValidationError

logger = logging.getLogger(__name__)

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_captcha(
    token: str | None, settings: Settings, *, client_ip: str | None = None
) -> None:
    """Raise unless ``token`` is a genuine Turnstile solution.

    Does nothing when no secret is configured.
    """
    secret = settings.turnstile_secret_key
    if not secret:
        return

    if not token:
        raise ValidationError("captcha.required", code="captcha_required")

    payload = {"secret": secret, "response": token}
    if client_ip:
        payload["remoteip"] = client_ip

    try:
        response = httpx.post(_VERIFY_URL, data=payload, timeout=10.0)
        response.raise_for_status()
        outcome = response.json()
    except (httpx.HTTPError, ValueError):
        # Logged with the failure attached. Refusing is deliberate: see above.
        logger.exception("Captcha verification could not be completed")
        raise ValidationError("captcha.unavailable", code="captcha_unavailable") from None

    if not outcome.get("success"):
        logger.warning(
            "Captcha rejected", extra={"error_codes": outcome.get("error-codes")}
        )
        raise ValidationError("captcha.failed", code="captcha_failed")
