"""A listing's official papers — upload and removal, for the owner.

The reviewer's side is in ``admin/businesses.py``: the metadata already rides
on the review payload through ``OwnerBusinessOut.documents``, so only the
download needs its own admin route.

Every route here goes through ``OwnedBusiness``, which loads the business by
id *and* checks the caller owns it — the scoping rule the Security Musts
state for `/api/my/*` and every owner-facing endpoint. There is deliberately
no public route: a commercial register is evidence for an administrator, not
content for a visitor.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.serializers import owner_business
from app.core.dependencies import AppSettings, DbSession, OwnedBusiness
from app.schemas.business import OwnerBusinessOut
from app.services.business_documents import BusinessDocumentService
from app.storage.factory import get_storage

router = APIRouter(tags=["business-documents"])


@router.post(
    "/businesses/{business_id}/documents",
    response_model=OwnerBusinessOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Commercial register, licence or permit")],
    label: Annotated[str | None, Form(max_length=120)] = None,
) -> OwnerBusinessOut:
    """Attach one official paper to the listing.

    Optional at every point: nothing about submission or publication consults
    these, so a business with no paperwork is not blocked by this route
    existing.
    """
    data = file.file.read()
    BusinessDocumentService(get_storage(), settings).store(
        db=db,
        business=business,
        data=data,
        original_filename=file.filename,
        label=label,
    )
    db.refresh(business)
    return owner_business(business)


@router.delete(
    "/businesses/{business_id}/documents/{document_id}", response_model=OwnerBusinessOut
)
def delete_document(
    document_id: uuid.UUID,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
) -> OwnerBusinessOut:
    BusinessDocumentService(get_storage(), settings).delete(
        db=db, business=business, document_id=document_id
    )
    db.refresh(business)
    return owner_business(business)
