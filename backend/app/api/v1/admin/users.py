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
from app.core.dependencies import AdminUser, AppSettings, DbSession, OtpProviderDep
from app.core.errors import NotFoundError, ValidationError
from app.models.enums import UserRole, VerificationDocumentKind
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository
from app.schemas.auth import IssuedPasswordOut
from app.schemas.moderation import AdminUserDetailOut
from app.schemas.verification import VerificationDocumentOut
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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    provider: OtpProviderDep,
) -> IssuedPasswordOut:
    """Issue a password for an account, and return it once.

    How an approved applicant gets in while no SMS or WhatsApp gateway is
    available: an administrator issues this and relays it over their own
    WhatsApp. The plaintext exists in this response and nowhere else — it is
    stored only as a hash, never logged, and cannot be read again. Issuing a
    second one replaces the first.

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

    password = AuthService(db, settings, provider).issue_password(user)
    return IssuedPasswordOut(phone_number=user.phone_number, password=password)
