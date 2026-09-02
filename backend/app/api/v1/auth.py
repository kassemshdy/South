"""Authentication endpoints: phone OTP for owners, password login for admins."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import (
    AppSettings,
    ClientIp,
    CurrentUser,
    DbSession,
    OtpProviderDep,
)
from app.schemas.auth import (
    AdminLoginIn,
    RequestOtpIn,
    RequestOtpOut,
    TokenOut,
    UpdateProfileIn,
    UserOut,
    VerifyOtpIn,
)
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/request-otp", response_model=RequestOtpOut)
def request_otp(
    payload: RequestOtpIn,
    db: DbSession,
    settings: AppSettings,
    provider: OtpProviderDep,
    client_ip: ClientIp,
) -> RequestOtpOut:
    """Send a one-time code to a Lebanese phone number."""
    service = AuthService(db, settings, provider)
    ttl, debug_code = service.request_otp(payload.phone_number, client_ip=client_ip)

    # Second guard on top of the provider's: the development code is only ever
    # returned to the client while running in development.
    return RequestOtpOut(
        expires_in_seconds=ttl,
        debug_code=debug_code if settings.is_development else None,
    )


@router.post("/auth/verify-otp", response_model=TokenOut)
def verify_otp(
    payload: VerifyOtpIn,
    db: DbSession,
    settings: AppSettings,
    provider: OtpProviderDep,
) -> TokenOut:
    """Verify the code, creating the account on first sign-in."""
    service = AuthService(db, settings, provider)
    user, token, expires_at = service.verify_otp(payload.phone_number, payload.code)
    return TokenOut(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


@router.post("/auth/admin/login", response_model=TokenOut)
def admin_login(
    payload: AdminLoginIn,
    db: DbSession,
    settings: AppSettings,
    provider: OtpProviderDep,
) -> TokenOut:
    service = AuthService(db, settings, provider)
    user, token, expires_at = service.login_admin(payload.email, payload.password)
    return TokenOut(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_me(payload: UpdateProfileIn, user: CurrentUser, db: DbSession) -> UserOut:
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip() or None
    db.commit()
    return UserOut.model_validate(user)
