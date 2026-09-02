"""Development OTP provider: logs the code instead of sending an SMS.

This keeps the whole authentication flow testable with no gateway credentials.
It refuses to be constructed outside development so the shortcut cannot leak
into production.
"""

from __future__ import annotations

import logging

from app.auth.otp.base import OtpSendResult
from app.core.config import Settings

logger = logging.getLogger(__name__)


class MockOtpProvider:
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        if settings.is_production:
            raise RuntimeError(
                "MockOtpProvider must never be used in production. "
                "Set OTP_PROVIDER to a real provider."
            )
        self._settings = settings

    def send(self, phone_number: str, code: str) -> OtpSendResult:
        logger.info(
            "OTP issued (development only)",
            extra={"phone_number": phone_number, "otp_code": code},
        )
        return OtpSendResult(delivered=True, provider=self.name, debug_code=code)

    def fixed_code(self) -> str | None:
        return self._settings.dev_fixed_otp_code
