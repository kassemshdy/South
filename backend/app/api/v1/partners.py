"""The partner form: anyone may send one, only an administrator reads them.

Round 3. Anonymous like a testimonial, so behind the same two guards as the
public applications -- a per-address limit and a site-wide one -- and the
captcha when one is configured. The public route only ever writes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.errors import NotFoundError, RateLimitedError
from app.core.i18n import translate
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.partner import PartnerRequest
from app.schemas.common import MessageResponse
from app.schemas.partner import PartnerRequestIn, PartnerRequestOut

public_router = APIRouter(tags=["partners"])
admin_router = APIRouter(prefix="/admin", tags=["admin-partners"])


@public_router.post(
    "/partners", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
def send_partner_request(
    payload: PartnerRequestIn, db: DbSession, settings: AppSettings, client_ip: ClientIp
) -> MessageResponse:
    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket="partner_ip",
                limit=settings.partner_per_ip_limit,
                window_seconds=settings.partner_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "partner.rate_limited")
    # Site-wide, so a sender rotating addresses still meets a ceiling.
    overall = limiter.hit(
        RateLimitRule(
            bucket="partner_global",
            limit=settings.partner_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "partner.rate_limited")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    db.add(PartnerRequest(**payload.model_dump(exclude={"captcha_token"})))
    db.commit()
    return MessageResponse(message=translate("partner.received"))


@admin_router.get("/partners", response_model=list[PartnerRequestOut])
def list_partner_requests(db: DbSession, admin: AdminUser) -> list[PartnerRequestOut]:
    """Newest first."""
    rows = db.execute(
        select(PartnerRequest).order_by(PartnerRequest.created_at.desc())
    ).scalars()
    return [PartnerRequestOut.model_validate(row) for row in rows]


@admin_router.delete("/partners/{request_id}", response_model=MessageResponse)
def delete_partner_request(
    request_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> MessageResponse:
    row = db.get(PartnerRequest, request_id)
    if row is None:
        raise NotFoundError("partner.not_found")
    db.delete(row)
    db.commit()
    return MessageResponse(message=translate("partner.deleted"))
