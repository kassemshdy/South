from __future__ import annotations

from functools import lru_cache

from app.auth.otp.base import OtpProvider
from app.auth.otp.mock import MockOtpProvider
from app.auth.otp.twilio import TwilioOtpProvider
from app.auth.otp.whatsapp import WhatsAppOtpProvider
from app.core.config import get_settings


@lru_cache
def get_otp_provider() -> OtpProvider:
    settings = get_settings()
    if settings.otp_provider == "twilio":
        return TwilioOtpProvider(settings)
    if settings.otp_provider == "whatsapp":
        return WhatsAppOtpProvider(settings)
    return MockOtpProvider(settings)
