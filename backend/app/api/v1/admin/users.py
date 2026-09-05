"""Per-user admin actions: today, just reading an owner's verification document.

The aggregate user list lives in ``admin/stats.py`` — this file is for actions
scoped to a single user, the same split ``admin/businesses.py`` follows for
single-business actions versus the list/pending endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.repositories.user import UserRepository
from app.schemas.verification import VerificationDocumentOut
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin", tags=["admin-users"])


def _load_document(db: DbSession, user_id: uuid.UUID):
    user = UserRepository(db).get(user_id)
    if user is None or user.verification_document is None:
        raise NotFoundError("verification.not_found")
    return user.verification_document


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
    document = _load_document(db, user_id)
    data = VerificationDocumentService(get_storage(), settings).read_bytes(document)
    filename = document.original_filename or f"{document.id}"
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
