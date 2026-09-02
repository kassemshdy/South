"""Twilio SMS provider.

Written against the same protocol as the mock so switching is a config change.
Uses the REST API over httpx rather than the Twilio SDK to keep dependencies
light; any other HTTP-based gateway can be adapted the same way.
"""

from __future__ import annotations

import logging

import httpx

from app.auth.otp.base import OtpSendResult
from app.core.config import Settings

logger = logging.getLogger(__name__)

_API_ROOT = "https://api.twilio.com/2010-04-01"


class TwilioOtpProvider:
    name = "twilio"

    def __init__(self, settings: Settings, *, timeout: float = 10.0) -> None:
        missing = [
            key
            for key, value in {
                "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
                "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
                "TWILIO_FROM_NUMBER": settings.twilio_from_number,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Twilio provider missing configuration: {', '.join(missing)}")

        self._account_sid = settings.twilio_account_sid or ""
        self._auth_token = settings.twilio_auth_token or ""
        self._from_number = settings.twilio_from_number or ""
        self._timeout = timeout

    def send(self, phone_number: str, code: str) -> OtpSendResult:
        body = f"رمز الدخول إلى دليل الجنوب: {code}"
        try:
            response = httpx.post(
                f"{_API_ROOT}/Accounts/{self._account_sid}/Messages.json",
                data={"To": phone_number, "From": self._from_number, "Body": body},
                auth=(self._account_sid, self._auth_token),
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            # Logged with the failure attached; the caller turns this into a
            # user-facing error rather than silently pretending success.
            logger.exception("Twilio OTP delivery failed", extra={"phone_number": phone_number})
            return OtpSendResult(delivered=False, provider=self.name)

        payload = response.json()
        return OtpSendResult(
            delivered=True, provider=self.name, provider_message_id=payload.get("sid")
        )

    def fixed_code(self) -> str | None:
        return None
