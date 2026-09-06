"""Authentication endpoints: phone OTP for owners, password login for admins."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.dependencies import (
    AppSettings,
    ClientIp,
    CurrentUser,
    DbSession,
    OtpProviderDep,
)
from app.models.enums import VerificationDocumentKind
from app.schemas.auth import (
    AdminLoginIn,
    RequestOtpIn,
    RequestOtpOut,
    TokenOut,
    UpdateProfileIn,
    UserOut,
    VerifyOtpIn,
)
from app.schemas.verification import VerificationDocumentOut
from app.services.auth import AuthService
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

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

    # Second guard on top of the provider's: the fixed code is only ever
    # returned to the client in environments that permit a mock provider.
    return RequestOtpOut(
        expires_in_seconds=ttl,
        debug_code=debug_code if settings.allows_mock_otp else None,
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
    # exclude_unset, not "is not None": a field explicitly sent as null must be
    # able to clear a previously-set value, not be indistinguishable from
    # "the caller didn't mention this field at all".
    data = payload.model_dump(exclude_unset=True)
    if "display_name" in data:
        user.display_name = (data["display_name"] or "").strip() or None
    if "personal_phone_number" in data:
        user.personal_phone_number = data["personal_phone_number"]
    db.commit()
    return UserOut.model_validate(user)


@router.get("/me/verification-document", response_model=VerificationDocumentOut | None)
def read_my_verification_document(user: CurrentUser) -> VerificationDocumentOut | None:
    """Metadata only, so the account page can show "uploaded on {date}"
    without ever fetching the bytes."""
    if user.verification_document is None:
        return None
    return VerificationDocumentOut.model_validate(user.verification_document)


@router.post(
    "/me/verification-document",
    response_model=VerificationDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_my_verification_document(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="A national ID, passport, or similar document")],
) -> VerificationDocumentOut:
    data = file.file.read()
    service = VerificationDocumentService(get_storage(), settings)
    document = service.store(
        db=db, user=user, data=data, original_filename=file.filename
    )
    return VerificationDocumentOut.model_validate(document)


@router.get("/me/cv-document", response_model=VerificationDocumentOut | None)
def read_my_cv_document(user: CurrentUser) -> VerificationDocumentOut | None:
    """Metadata only, like the ID document above — a CV is a personal
    document and never gets a public URL either."""
    if user.cv_document is None:
        return None
    return VerificationDocumentOut.model_validate(user.cv_document)


@router.post(
    "/me/cv-document",
    response_model=VerificationDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_my_cv_document(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="A CV as PDF or an image scan")],
) -> VerificationDocumentOut:
    data = file.file.read()
    service = VerificationDocumentService(get_storage(), settings)
    document = service.store(
        db=db,
        user=user,
        data=data,
        original_filename=file.filename,
        kind=VerificationDocumentKind.CV,
    )
    return VerificationDocumentOut.model_validate(document)
