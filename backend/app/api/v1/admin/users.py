"""Per-user admin actions: viewing a single account's detail (its businesses
and talent profile, in any status) and reading an owner's verification
document.

The aggregate user list lives in ``admin/stats.py`` — this file is for actions
scoped to a single user, the same split ``admin/businesses.py`` follows for
single-business actions versus the list/pending endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from app.api.serializers import admin_user_detail
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.downloads import content_disposition
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.i18n import translate
from app.models.enums import UserRole, VerificationDocumentKind
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository
from app.schemas.auth import CredentialStateOut, IssuedPasswordOut
from app.schemas.common import MessageResponse
from app.schemas.moderation import AdminUserDetailOut
from app.schemas.verification import VerificationDocumentOut
from app.services.account import AccountDeletionService
from app.services.auth import AuthService
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin", tags=["admin-users"])


def _load_document(
    db: DbSession,
    user_id: uuid.UUID,
    kind: VerificationDocumentKind = VerificationDocumentKind.IDENTITY,
):
    user = UserRepository(db).get(user_id)
    document = user.document_of(kind) if user is not None else None
    if document is None:
        raise NotFoundError("verification.not_found")
    return document


def _download(document, settings: AppSettings) -> Response:
    data = VerificationDocumentService(get_storage(), settings).read_bytes(document)
    filename = document.original_filename or f"{document.id}"
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def get_user(user_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminUserDetailOut:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise NotFoundError("user.not_found")
    businesses = BusinessRepository(db).list_for_owner(user_id)
    talent_profile = TalentRepository(db).get_for_owner(user_id)
    return admin_user_detail(user, businesses=businesses, talent_profile=talent_profile)


@router.get(
    "/users/{user_id}/verification-document", response_model=VerificationDocumentOut
)
def get_verification_document(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> VerificationDocumentOut:
    return VerificationDocumentOut.model_validate(_load_document(db, user_id))


@router.get("/users/{user_id}/verification-document/download")
def download_verification_document(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> Response:
    return _download(_load_document(db, user_id), settings)


@router.get(
    "/users/{user_id}/verification-document-back", response_model=VerificationDocumentOut
)
def get_verification_document_back(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> VerificationDocumentOut:
    """The reverse of the ID card, which carries the place of registration."""
    return VerificationDocumentOut.model_validate(
        _load_document(db, user_id, VerificationDocumentKind.IDENTITY_BACK)
    )


@router.get("/users/{user_id}/verification-document-back/download")
def download_verification_document_back(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> Response:
    return _download(
        _load_document(db, user_id, VerificationDocumentKind.IDENTITY_BACK), settings
    )


@router.get("/users/{user_id}/cv-document", response_model=VerificationDocumentOut)
def get_cv_document(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> VerificationDocumentOut:
    return VerificationDocumentOut.model_validate(
        _load_document(db, user_id, VerificationDocumentKind.CV)
    )


@router.get("/users/{user_id}/cv-document/download")
def download_cv_document(
    user_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> Response:
    return _download(_load_document(db, user_id, VerificationDocumentKind.CV), settings)


@router.post("/users/{user_id}/credentials", response_model=IssuedPasswordOut)
def issue_credentials(
    user_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    settings: AppSettings,
) -> IssuedPasswordOut:
    """Issue a password for an account, and return it once.

    How an approved applicant gets in: an administrator issues this and
    relays it over their own WhatsApp — there is no other way onto the site.
    The plaintext exists in this response and nowhere else — it is stored only
    as a hash, never logged, and cannot be read again. Issuing a second one
    replaces the first.

    Refused for an administrator account: an admin password is not something
    another admin hands out, and the account it is issued to must be one that
    signs in at /auth/login.
    """
    user = UserRepository(db).get(user_id)
    if user is None:
        raise NotFoundError("user.not_found")
    if user.role is UserRole.ADMIN:
        raise ValidationError("user.credentials_not_for_admin", code="admin_account")
    if user.phone_number is None:
        # Nothing to sign in with, and nowhere to send it.
        raise ValidationError("user.credentials_need_phone", code="missing_phone")

    password = AuthService(db, settings).issue_password(user)
    return IssuedPasswordOut(
        phone_number=user.phone_number, password=password, version=user.token_version
    )


@router.get("/users/{user_id}/credentials", response_model=CredentialStateOut)
def credential_state(user_id: uuid.UUID, admin: AdminUser, db: DbSession) -> CredentialStateOut:
    """Whether the password an administrator's browser remembers is current.

    The owners asked for an issued password to stay on screen until it is
    replaced (ticket, 26 Oct 2026). The server still keeps only a hash; the
    browser keeps the plaintext with the version it was issued at, and this
    says whether that version is still the account's.
    """
    user = UserRepository(db).get(user_id)
    if user is None:
        raise NotFoundError("user.not_found")
    return CredentialStateOut(
        version=user.token_version, has_password=user.password_hash is not None
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(user_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    """Delete a seller's account and everything it published, files included.

    The same deletion an owner can ask for themselves. Never an administrator
    account: that is the way into moderation, and this route must not be a
    way to lock the platform's owners out of their own site.
    """
    user = UserRepository(db).get(user_id)
    if user is None:
        raise NotFoundError("user.not_found")
    if user.role is UserRole.ADMIN:
        raise PermissionDeniedError("account.admin_cannot_delete")
    AccountDeletionService(db, get_storage()).delete(user)
    return MessageResponse(message=translate("user.deleted"))
