"""WhatsApp Cloud API provider.

Delivers the code as a WhatsApp *authentication template* message rather than
an SMS. Written against the same protocol as the mock and Twilio adapters, so
choosing it is a configuration change.

Two things about this provider differ from the SMS one, and both are
consequences of how Meta works rather than choices made here:

**The message text is not ours.** An authentication template is registered
with Meta, reviewed, and then referenced by name; the only thing this code
sends is the code itself, substituted into the approved body. So
``auth.sms.body`` in the locale catalogs is not what a WhatsApp recipient
reads — the Arabic wording lives in the template. Registering an ``ar``
template is therefore part of configuring this provider, not an optional
nicety, and it is the one documented exception to this project's rule that
every user-facing string lives in a catalog.

**Failures are worth reading.** Meta answers a rejected send with a JSON body
naming the reason (an unapproved template, a recipient outside the test
allow-list, a component the template does not declare), and that body is the
difference between a five-minute fix and an afternoon. It is logged. The
access token travels in the Authorization header and never appears in a
response body, so logging the body leaks nothing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.otp.base import OtpSendResult
from app.core.config import Settings

logger = logging.getLogger(__name__)

_API_ROOT = "https://graph.facebook.com/v21.0"


class WhatsAppOtpProvider:
    name = "whatsapp"

    def __init__(self, settings: Settings, *, timeout: float = 10.0) -> None:
        missing = [
            key
            for key, value in {
                "WHATSAPP_PHONE_NUMBER_ID": settings.whatsapp_phone_number_id,
                "WHATSAPP_ACCESS_TOKEN": settings.whatsapp_access_token,
                "WHATSAPP_TEMPLATE_NAME": settings.whatsapp_template_name,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"WhatsApp provider missing configuration: {', '.join(missing)}")

        self._phone_number_id = settings.whatsapp_phone_number_id or ""
        self._access_token = settings.whatsapp_access_token or ""
        self._template_name = settings.whatsapp_template_name or ""
        self._template_locale = settings.whatsapp_template_locale
        self._template_has_button = settings.whatsapp_template_has_button
        self._timeout = timeout

    def _payload(self, phone_number: str, code: str) -> dict[str, Any]:
        """The Cloud API message body.

        An authentication template takes the code twice: once for the sentence
        and once for the button that copies it, which is why the same value
        appears in two components. A template created without a button rejects
        the second one, so it is configurable rather than assumed — see
        ``WHATSAPP_TEMPLATE_HAS_BUTTON``.
        """
        components: list[dict[str, Any]] = [
            {"type": "body", "parameters": [{"type": "text", "text": code}]}
        ]
        if self._template_has_button:
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": code}],
                }
            )

        return {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": self._template_name,
                "language": {"code": self._template_locale},
                "components": components,
            },
        }

    def send(self, phone_number: str, code: str) -> OtpSendResult:
        try:
            response = httpx.post(
                f"{_API_ROOT}/{self._phone_number_id}/messages",
                json=self._payload(phone_number, code),
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "WhatsApp OTP delivery rejected",
                extra={
                    "phone_number": phone_number,
                    "status_code": exc.response.status_code,
                    # Meta's own explanation, which names the actual problem.
                    "provider_error": exc.response.text[:500],
                },
            )
            return OtpSendResult(delivered=False, provider=self.name)
        except httpx.HTTPError:
            logger.exception("WhatsApp OTP delivery failed", extra={"phone_number": phone_number})
            return OtpSendResult(delivered=False, provider=self.name)

        payload = response.json()
        messages = payload.get("messages") or [{}]
        return OtpSendResult(
            delivered=True, provider=self.name, provider_message_id=messages[0].get("id")
        )

    def fixed_code(self) -> str | None:
        return None
