"""Sign-up and password reset by SMS code. See app/services/phone_auth.py."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.i18n import translate
from app.schemas.auth import TokenOut, UserOut
from app.schemas.common import MessageResponse
from app.schemas.phone_auth import (
    PhoneAuthConfigOut,
    PhoneCodeCheckIn,
    PhoneCodeCompleteIn,
    PhoneCodeIn,
    SmsSignupSettingsIn,
    SmsSignupSettingsOut,
)
from app.services.phone_auth import PhoneAuthService, read_config, write_config

router = APIRouter(tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/auth/phone/config", response_model=PhoneAuthConfigOut)
def phone_auth_config(db: DbSession, settings: AppSettings) -> PhoneAuthConfigOut:
    return PhoneAuthConfigOut(enabled=PhoneAuthService(db, settings).available())


@router.post(
    "/auth/phone/code", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
def send_phone_code(
    payload: PhoneCodeIn, db: DbSession, settings: AppSettings, client_ip: ClientIp
) -> MessageResponse:
    """Send a code by SMS. The same answer whether or not the number has an
    account."""
    PhoneAuthService(db, settings).request_code(
        payload.phone, captcha_token=payload.captcha_token, client_ip=client_ip
    )
    return MessageResponse(message=translate("phoneAuth.sent"))


@router.post("/auth/phone/check", response_model=MessageResponse)
def check_phone_code(
    payload: PhoneCodeCheckIn, db: DbSession, settings: AppSettings
) -> MessageResponse:
    """Is the code right? Spends one of the code's guesses."""
    PhoneAuthService(db, settings).check_code(payload.phone, payload.code)
    return MessageResponse(message=translate("phoneAuth.code_ok"))


@router.post("/auth/phone/complete", response_model=TokenOut)
def complete_phone_signup(
    payload: PhoneCodeCompleteIn, db: DbSession, settings: AppSettings
) -> TokenOut:
    """Use the code with a new password: opens the account if there is none,
    otherwise replaces its password. Signs in."""
    user, token, expires_at = PhoneAuthService(db, settings).complete(
        payload.phone, payload.code, payload.password
    )
    return TokenOut(access_token=token, expires_at=expires_at, user=UserOut.model_validate(user))


def _admin_settings(db: DbSession, settings: AppSettings) -> SmsSignupSettingsOut:
    config = read_config(db)
    service = PhoneAuthService(db, settings)
    return SmsSignupSettingsOut(
        enabled=config.enabled,
        daily_cap=config.daily_cap,
        sms_configured=settings.sms_enabled,
        sent_today=service.sent_today(),
    )


@admin_router.get("/site-settings/sms-signup", response_model=SmsSignupSettingsOut)
def sms_signup_settings(
    db: DbSession, settings: AppSettings, admin: AdminUser
) -> SmsSignupSettingsOut:
    return _admin_settings(db, settings)


@admin_router.put("/site-settings/sms-signup", response_model=SmsSignupSettingsOut)
def set_sms_signup_settings(
    payload: SmsSignupSettingsIn, db: DbSession, settings: AppSettings, admin: AdminUser
) -> SmsSignupSettingsOut:
    write_config(db, enabled=payload.enabled, daily_cap=payload.daily_cap)
    return _admin_settings(db, settings)
