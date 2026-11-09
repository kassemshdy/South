"""Sign-up and password reset by SMS code (app/services/phone_auth.py)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhoneAuthConfigOut(BaseModel):
    #: Whether the site offers sign-up by SMS code right now; when false the
    #: client shows the application form instead.
    enabled: bool


class PhoneCodeIn(BaseModel):
    phone: str = Field(min_length=6, max_length=25)
    captcha_token: str | None = Field(default=None, max_length=4096)


class PhoneCodeCheckIn(BaseModel):
    phone: str = Field(min_length=6, max_length=25)
    code: str = Field(min_length=4, max_length=10)


class PhoneCodeCompleteIn(PhoneCodeCheckIn):
    password: str = Field(min_length=8, max_length=200)


class SmsSignupSettingsIn(BaseModel):
    enabled: bool
    daily_cap: int = Field(ge=1, le=5000)


class SmsSignupSettingsOut(SmsSignupSettingsIn):
    #: Whether the SMS provider's keys are set; without them the switch does
    #: nothing.
    sms_configured: bool
    sent_today: int
