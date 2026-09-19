"""Administrator moderation endpoints.

Every route here depends on ``AdminUser``; there is no code path that reaches a
moderation action without that check.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.serializers import admin_business, paginate
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError
from app.models.enums import BusinessStatus
from app.repositories.business import BusinessRepository
from app.schemas.common import PaginatedResponse
from app.schemas.moderation import AdminBusinessOut, RejectIn, SuspendIn
from app.services.business_documents import BusinessDocumentService
from app.services.moderation import ModerationService
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin", tags=["admin-businesses"])


def _load(db: DbSession, business_id: uuid.UUID):
    business = BusinessRepository(db).get_for_admin(business_id)
    if business is None:
        raise NotFoundError("business.not_found")
    return business


@router.get("/businesses", response_model=PaginatedResponse[AdminBusinessOut])
def list_businesses(
    db: DbSession,
    admin: AdminUser,
    status: Annotated[BusinessStatus | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminBusinessOut]:
    results = BusinessRepository(db).list_for_admin(
        status=status, q=q, page=page, page_size=page_size
    )
    return paginate(results, admin_business)


@router.get("/businesses/pending", response_model=PaginatedResponse[AdminBusinessOut])
def list_pending(
    db: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminBusinessOut]:
    """The review queue, oldest submission first."""
    results = BusinessRepository(db).list_for_admin(
        status=BusinessStatus.PENDING_REVIEW, page=page, page_size=page_size
    )
    return paginate(results, admin_business)


@router.get("/businesses/{business_id}", response_model=AdminBusinessOut)
def get_business(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    return admin_business(_load(db, business_id))


@router.get("/businesses/{business_id}/documents/{document_id}/download")
def download_document(
    business_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> Response:
    """Read one of the listing's official papers.

    The only way to the bytes. ``BusinessDocument`` has no public url column
    and no public route, so a commercial register — which names the owner and
    the establishment's address — is reachable by an administrator and nobody
    else, the same boundary an identity document keeps.
    """
    business = _load(db, business_id)
    document = next((d for d in business.documents if d.id == document_id), None)
    if document is None:
        raise NotFoundError("business_document.not_found")

    data = BusinessDocumentService(get_storage(), settings).read_bytes(document)
    filename = document.original_filename or f"{document.id}"
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/businesses/{business_id}/approve", response_model=AdminBusinessOut)
def approve(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    business = ModerationService(db).approve(_load(db, business_id), admin)
    return admin_business(business)


@router.post("/businesses/{business_id}/reject", response_model=AdminBusinessOut)
def reject(
    business_id: uuid.UUID, payload: RejectIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    business = ModerationService(db).reject(_load(db, business_id), admin, payload.reason)
    return admin_business(business)


@router.post("/businesses/{business_id}/suspend", response_model=AdminBusinessOut)
def suspend(
    business_id: uuid.UUID, payload: SuspendIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    business = ModerationService(db).suspend(_load(db, business_id), admin, payload.reason)
    return admin_business(business)


@router.post("/businesses/{business_id}/reactivate", response_model=AdminBusinessOut)
def reactivate(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    business = ModerationService(db).reactivate(_load(db, business_id), admin)
    return admin_business(business)
