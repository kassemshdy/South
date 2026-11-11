"""Administrator moderation endpoints.

Every route here depends on ``AdminUser``; there is no code path that reaches a
moderation action without that check.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.api.serializers import admin_business, paginate
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.downloads import content_disposition
from app.core.errors import AppError, NotFoundError, PayloadTooLargeError, ValidationError
from app.core.i18n import translate
from app.core.uploads import read_at_most
from app.database.session import SessionLocal
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, ImageKind
from app.repositories.business import AdminSort, BusinessRepository
from app.schemas.business import BusinessUpdateIn
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.growth_report import ShopViewsOut
from app.schemas.moderation import (
    AdminBusinessOut,
    CategoryChangeIn,
    GoodsOriginIn,
    MoveItemsIn,
    OutreachIn,
    PlaceChangeIn,
    RejectIn,
    SmsIn,
    SmsSentOut,
    SmsStatusOut,
    SuspendIn,
)
from app.services import social_followers, staff_notices, telegram_archive
from app.services.account import AccountDeletionService
from app.services.business import BusinessService
from app.services.business_documents import BusinessDocumentService
from app.services.business_images import store_business_image
from app.services.growth_report import GrowthReportService
from app.services.moderation import ModerationService
from app.services.sms import SmsError, SmsService
from app.storage.factory import get_storage

logger = logging.getLogger(__name__)

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
    without_products: Annotated[
        bool, Query(description="Only shops with nothing on sale, to contact them")
    ] = False,
    with_products: Annotated[
        bool, Query(description="Only shops with at least one product on sale")
    ] = False,
    contacted: Annotated[
        bool | None, Query(description="Only shops staff have (true) or have not (false) contacted")
    ] = None,
    sort: Annotated[
        AdminSort, Query(description="newest, or most Instagram/Facebook followers")
    ] = "newest",
    category: Annotated[str | None, Query(description="Category slug")] = None,
    location: Annotated[
        str | None, Query(description="Location slug; a district includes its towns")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminBusinessOut]:
    results = BusinessRepository(db).list_for_admin(
        sort=sort,
        category_slug=category,
        location_slug=location,
        status=status,
        q=q,
        without_products=without_products,
        with_products=with_products,
        contacted=contacted,
        page=page,
        page_size=page_size,
    )
    return paginate(results, admin_business)


class OutreachCountsOut(BaseModel):
    """Tab sizes for the staff follow-up page (approved shops only)."""

    not_contacted: int
    contacted: int
    uploaded: int


@router.get("/businesses/outreach-counts", response_model=OutreachCountsOut)
def outreach_counts(db: DbSession, admin: AdminUser) -> OutreachCountsOut:
    not_contacted, contacted, uploaded = BusinessRepository(db).outreach_counts()
    return OutreachCountsOut(not_contacted=not_contacted, contacted=contacted, uploaded=uploaded)


@router.get("/businesses/pending", response_model=PaginatedResponse[AdminBusinessOut])
def list_pending(
    db: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[AdminBusinessOut]:
    """The review queue, newest submission first."""
    results = BusinessRepository(db).list_for_admin(
        status=BusinessStatus.PENDING_REVIEW, page=page, page_size=page_size
    )
    return paginate(results, admin_business)


@router.put("/businesses/{business_id}/outreach", response_model=AdminBusinessOut)
def set_outreach(
    business_id: uuid.UUID, body: OutreachIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    """Record that staff contacted a shop, with a note, or clear it (the
    owners' request, 6 Nov 2026, for the shops with nothing on sale)."""
    business = _load(db, business_id)
    if body.contacted:
        note = (body.note or "").strip() or None
        if business.outreach_contacted_at is None:
            business.outreach_contacted_at = datetime.now(UTC)
        business.outreach_contacted_by = admin.id
        business.outreach_note = note
    else:
        business.outreach_contacted_at = None
        business.outreach_contacted_by = None
        business.outreach_note = None
    db.commit()
    if body.contacted:
        # The team sees each follow-up as it is written: the shop, the note
        # and who wrote it (the owners' request, 7 Nov 2026).
        telegram_archive.notify(
            telegram_archive.Notice(
                title_key="telegram.kind.outreach",
                rows=[
                    ("shop", business.name),
                    ("note", business.outreach_note),
                    ("staff", staff_notices.staff_name(admin)),
                ],
                path=f"/admin/businesses/{business.id}",
            )
        )
    return admin_business(_load(db, business_id))


@router.get("/businesses/{business_id}", response_model=AdminBusinessOut)
def get_business(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    return admin_business(_load(db, business_id))


VIEWS_DAYS = 30


@router.get("/businesses/{business_id}/views", response_model=ShopViewsOut)
def business_views(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> ShopViewsOut:
    """The shop's views over 30 days, for the WhatsApp message that tells
    its owner people are looking (the owners' request, 9 Nov 2026)."""
    business = _load(db, business_id)
    page, products = GrowthReportService(db).shop_views(business.id, VIEWS_DAYS)
    return ShopViewsOut(days=VIEWS_DAYS, page_views=page, product_views=products)


@router.post("/businesses/followers/refresh", response_model=MessageResponse)
def refresh_followers(
    background: BackgroundTasks, settings: AppSettings, admin: AdminUser
) -> MessageResponse:
    """Read every shop's follower counts now rather than at the next daily
    run. Answers at once; the counts arrive in a few minutes."""
    if not settings.apify_token:
        raise AppError("followers.not_configured", code="followers_not_configured", status_code=503)
    token = settings.apify_token

    def run() -> None:
        with httpx.Client(timeout=330) as client, SessionLocal() as session:
            social_followers.refresh(session, social_followers.ApifyFollowers(token, client))

    background.add_task(run)
    return MessageResponse(message=translate("followers.refresh_started"))


@router.get("/sms", response_model=SmsStatusOut)
def sms_status(settings: AppSettings, admin: AdminUser) -> SmsStatusOut:
    """Whether SMS is set up, so the screens show the button only then."""
    service = SmsService(settings)
    if not service.enabled:
        return SmsStatusOut(enabled=False)
    try:
        balance = service.balance()
    except httpx.HTTPError:
        balance = None
    return SmsStatusOut(enabled=True, balance=balance)


@router.post("/businesses/{business_id}/sms", response_model=SmsSentOut)
def send_sms(
    business_id: uuid.UUID,
    payload: SmsIn,
    db: DbSession,
    settings: AppSettings,
    admin: AdminUser,
) -> SmsSentOut:
    """Text the shop owner's account number -- the number they sign in
    with, not the shop's published one (the owners' request, 9 Nov 2026)."""
    business = _load(db, business_id)
    service = SmsService(settings)
    if not service.enabled:
        raise AppError("sms.not_configured", code="sms_not_configured", status_code=503)
    number = business.owner.phone_number if business.owner else None
    if not number:
        raise ValidationError("sms.no_number", code="sms_no_number")
    try:
        sent = service.send(number, payload.message)
    except (SmsError, httpx.HTTPError) as error:
        raise AppError(
            "sms.refused", code="sms_refused", status_code=502, params={"reason": str(error)}
        ) from error
    return SmsSentOut(confirmation_id=sent.confirmation_id, parts=sent.parts)


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
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.post("/businesses/drafts/send-to-review", response_model=MessageResponse)
def send_all_drafts_to_review(db: DbSession, admin: AdminUser) -> MessageResponse:
    """Every draft shop into the review queue at once (see send_to_review)."""
    drafts = db.scalars(select(Business).where(Business.status == BusinessStatus.DRAFT)).all()
    service = ModerationService(db)
    for business in drafts:
        service.send_to_review(business, admin)
    return MessageResponse(message=translate("admin.drafts_sent", count=len(drafts)))


@router.post("/businesses/{business_id}/send-to-review", response_model=AdminBusinessOut)
def send_to_review(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    """One draft, or a rejected shop, into the review queue on its owner's
    behalf."""
    business = ModerationService(db).send_to_review(_load(db, business_id), admin)
    return admin_business(business)


@router.post("/businesses/{business_id}/approve", response_model=AdminBusinessOut)
def approve(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminBusinessOut:
    business = ModerationService(db).approve(_load(db, business_id), admin)
    staff_notices.moderated(
        approved=True,
        listing="shop",
        name=business.name,
        admin=admin,
        reason=None,
        path=f"/admin/businesses/{business.id}",
    )
    return admin_business(business)


@router.post("/businesses/{business_id}/reject", response_model=AdminBusinessOut)
def reject(
    business_id: uuid.UUID, payload: RejectIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    business = ModerationService(db).reject(_load(db, business_id), admin, payload.reason)
    staff_notices.moderated(
        approved=False,
        listing="shop",
        name=business.name,
        admin=admin,
        reason=payload.reason,
        path=f"/admin/businesses/{business.id}",
    )
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


# --- Permanent deletion -----------------------------------------------------
#
# The owners asked for it (round 3): suspending hides a listing, this removes
# it and every file it pointed at, for good. The owner's account stays; it is
# deleted on its own from the user's page.


@router.delete("/businesses/{business_id}", response_model=MessageResponse)
def delete_business(business_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    AccountDeletionService(db, get_storage()).delete_business(_load(db, business_id))
    return MessageResponse(message=translate("business.deleted"))


@router.delete("/businesses/{business_id}/items/{item_id}", response_model=MessageResponse)
def delete_item(
    business_id: uuid.UUID, item_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> MessageResponse:
    business = _load(db, business_id)
    # Scoped by business, as the owner's route is: an item id from another
    # listing reaches nothing.
    item = db.get(BusinessItem, item_id)
    if item is None or item.business_id != business.id:
        raise NotFoundError("item.not_found")
    AccountDeletionService(db, get_storage()).delete_item(item)
    BusinessService(db).refresh_search_text(business)
    db.commit()
    return MessageResponse(message=translate("item.deleted"))


@router.post("/businesses/{business_id}/items/move", response_model=AdminBusinessOut)
def move_items(
    business_id: uuid.UUID, body: MoveItemsIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    """Move every product of a listing to another listing of the same owner.

    For an owner who added their products to a second, never-submitted shop
    instead of the approved one (the owners' report, 7 Nov 2026). The rows
    move, their photos stay where they are, so deleting the emptied listing
    afterwards leaves them alone. Returns the target.
    """
    source = _load(db, business_id)
    target = _load(db, body.target_business_id)
    if target.id == source.id or target.owner_id != source.owner_id:
        raise ValidationError("business.move_items_invalid", code="move_items_invalid")
    after = db.scalar(
        select(func.coalesce(func.max(BusinessItem.sort_order), -1)).where(
            BusinessItem.business_id == target.id
        )
    )
    moved = db.execute(
        update(BusinessItem)
        .where(BusinessItem.business_id == source.id)
        .values(business_id=target.id, sort_order=BusinessItem.sort_order + (after or 0) + 1)
        .execution_options(synchronize_session=False)
    ).rowcount
    db.expire_all()
    service = BusinessService(db)
    service.refresh_search_text(_load(db, source.id))
    service.refresh_search_text(_load(db, target.id))
    db.commit()
    logger.info(
        "Products moved between listings",
        extra={"from": str(source.id), "to": str(target.id), "count": moved, "by": str(admin.id)},
    )
    return admin_business(_load(db, target.id))


# --- Corrections an administrator makes on an owner's behalf ----------------


@router.post("/businesses/{business_id}/goods-origin", response_model=AdminBusinessOut)
def set_goods_origin(
    business_id: uuid.UUID, payload: GoodsOriginIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    """Move a listing between the local and imported doors.

    An owner chooses by the door they came through, and some came through
    the wrong one. Every product moves with the listing: a product's own mark
    is what the directory filters on, so leaving them behind would keep the
    shop under the door it was just taken out of. An owner who sells both can
    still mark a product differently afterwards.
    """
    business = _load(db, business_id)
    business.goods_origin = payload.goods_origin
    for item in business.items:
        item.goods_origin = payload.goods_origin
    db.commit()
    return admin_business(_load(db, business_id))


@router.post("/businesses/{business_id}/category", response_model=AdminBusinessOut)
def set_category(
    business_id: uuid.UUID, payload: CategoryChangeIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    """Correct the category a shop is filed under, at any status.

    Through the owner's own update path, so the category is validated and
    the search text rebuilt as when they edit it.
    """
    BusinessService(db).update(
        _load(db, business_id),
        BusinessUpdateIn(
            category_id=payload.category_id,
            custom_category_text=payload.custom_category_text,
        ),
    )
    return admin_business(_load(db, business_id))


@router.post("/businesses/{business_id}/place", response_model=AdminBusinessOut)
def set_place(
    business_id: uuid.UUID, payload: PlaceChangeIn, db: DbSession, admin: AdminUser
) -> AdminBusinessOut:
    """Correct a shop's town and map pin -- for a pin put across the border,
    or a town that is not where the shop is."""
    BusinessService(db).update(
        _load(db, business_id),
        BusinessUpdateIn(
            location_id=payload.location_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        ),
    )
    return admin_business(_load(db, business_id))


@router.post("/businesses/{business_id}/images", response_model=AdminBusinessOut)
def upload_brand_image(
    business_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    admin: AdminUser,
    file: Annotated[UploadFile, File(description="Image file")],
    kind: Annotated[ImageKind, Form()] = ImageKind.LOGO,
) -> AdminBusinessOut:
    """A logo or cover for a listing that went live without one -- the owners
    asked how a listing could be given a logo when its owner had not added
    one. Logo and cover only: the gallery and products stay the owner's."""
    if kind not in (ImageKind.LOGO, ImageKind.COVER):
        raise ValidationError("image.invalid_kind", code="invalid_image_kind")
    data = read_at_most(file.file, settings.max_upload_bytes)
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()
    business = _load(db, business_id)
    store_business_image(
        db, settings, business, kind=kind, data=data, content_type=file.content_type
    )
    db.commit()
    return admin_business(_load(db, business_id))

