"""Authentication endpoints: one sign-in form, and the account's own settings."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.dependencies import (
    AppSettings,
    ClientIp,
    CurrentUser,
    DbSession,
    SignedInUser,
)
from app.core.errors import AuthenticationError, PayloadTooLargeError
from app.core.security import verify_password
from app.models.enums import ImageKind, VerificationDocumentKind
from app.schemas.auth import (
    AdminLoginIn,
    ChangePasswordIn,
    LoginIn,
    TokenOut,
    UpdateProfileIn,
    UserOut,
)
from app.schemas.identity import IDENTITY_FIELDS
from app.schemas.verification import VerificationDocumentOut
from app.services.auth import AuthService
from app.services.images import ImageService
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

router = APIRouter(tags=["auth"])


@router.post("/auth/admin/login", response_model=TokenOut)
def admin_login(
    payload: AdminLoginIn,
    db: DbSession,
    settings: AppSettings,
) -> TokenOut:
    """The administrators-only door, deliberately unlinked.

    /auth/login signs an administrator in too, and the form that calls it is
    the one anybody is shown. This stays for two reasons: an administrator
    locked out of a deployment has nobody to ask, and `mcp-server` signs in
    here rather than through a form.
    """
    service = AuthService(db, settings)
    user, token, expires_at = service.login_admin(payload.email, payload.password)
    return TokenOut(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


@router.post("/auth/login", response_model=TokenOut)
def login(
    payload: LoginIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> TokenOut:
    """Sign in with a phone number or an email address, and a password.

    The only sign-in route a client calls. It takes owners and administrators
    alike: the account's role decides what the token opens, not which form it
    was typed into.
    """
    service = AuthService(db, settings)
    user, token, expires_at = service.login(
        payload.identifier, payload.password, client_ip=client_ip
    )
    return TokenOut(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


@router.post("/me/password", response_model=UserOut)
def change_my_password(
    payload: ChangePasswordIn,
    user: SignedInUser,
    db: DbSession,
    settings: AppSettings,
) -> UserOut:
    """Replace one's own password, ending every other session.

    Reachable while ``must_change_password`` is set — it is the one thing such
    an account may do.
    """
    service = AuthService(db, settings)
    if not verify_password(payload.current_password, user.password_hash):
        raise AuthenticationError("auth.invalid_credentials", code="invalid_credentials")
    service.set_password(user, payload.new_password)
    return UserOut.model_validate(user)


@router.get("/me", response_model=UserOut)
def read_me(user: SignedInUser) -> UserOut:
    """Readable even while a password change is outstanding: the client needs
    this to know that it is."""
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
    # The identity block is set here rather than per listing, so one account
    # holds one legal name however many businesses it owns.
    for field in IDENTITY_FIELDS:
        if field in data:
            setattr(user, field, data[field])
    db.commit()
    return UserOut.model_validate(user)


@router.post("/me/photo", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def upload_my_photo(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Image file")],
) -> UserOut:
    """Replace the account holder's own photo.

    Processed through ``ImageService`` rather than stored as sent, for the
    reason every image here is: the bytes are decoded, resized and re-encoded,
    so nothing a client uploads is ever served back verbatim. ``LOGO`` is the
    variant — square and 600px, which is what a headshot wants — and is the
    same one a talent profile photo uses.

    The previous file is deleted rather than orphaned, since an account has
    exactly one photo and a bucket of abandoned faces is its own problem.
    """
    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()

    service = ImageService(get_storage(), settings)
    stored = service.process_and_store(
        data=data,
        content_type=file.content_type,
        owner_id=user.id,
        kind=ImageKind.LOGO,
        prefix="owner",
    )

    if user.photo_storage_key:
        service.delete(user.photo_storage_key)

    user.photo_url, user.photo_storage_key = stored.url, stored.key
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/me/photo", response_model=UserOut)
def delete_my_photo(user: CurrentUser, db: DbSession, settings: AppSettings) -> UserOut:
    """Remove the photo, file included."""
    if user.photo_storage_key:
        ImageService(get_storage(), settings).delete(user.photo_storage_key)
    user.photo_url, user.photo_storage_key = None, None
    db.commit()
    db.refresh(user)
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


@router.get(
    "/me/verification-document-back", response_model=VerificationDocumentOut | None
)
def read_my_verification_document_back(
    user: CurrentUser,
) -> VerificationDocumentOut | None:
    """The reverse of the ID card. Metadata only, like the front."""
    document = user.verification_document_back
    if document is None:
        return None
    return VerificationDocumentOut.model_validate(document)


@router.post(
    "/me/verification-document-back",
    response_model=VerificationDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_my_verification_document_back(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="The back of the ID card")],
) -> VerificationDocumentOut:
    data = file.file.read()
    service = VerificationDocumentService(get_storage(), settings)
    document = service.store(
        db=db,
        user=user,
        data=data,
        original_filename=file.filename,
        kind=VerificationDocumentKind.IDENTITY_BACK,
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
