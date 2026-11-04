"""Open service requests: a visitor asks the team for a service.

The owners' services redesign (3 Nov 2026). Anonymous, behind the same
guards as the partner form -- a per-address limit, a site-wide one and the
captcha when one is configured. The public route only writes; staff read
the requests, find a suitable provider and archive them when handled.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.errors import NotFoundError, RateLimitedError, ValidationError
from app.core.i18n import translate
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.open_service_request import OpenServiceRequest
from app.models.talent import TalentSkill
from app.models.taxonomy import Location
from app.schemas.common import MessageResponse
from app.schemas.open_service_request import OpenServiceRequestIn, OpenServiceRequestOut

public_router = APIRouter(tags=["open-service-requests"])
admin_router = APIRouter(prefix="/admin", tags=["admin-open-service-requests"])


def _out(row: OpenServiceRequest) -> OpenServiceRequestOut:
    return OpenServiceRequestOut(
        id=row.id,
        customer_name=row.customer_name,
        customer_phone=row.customer_phone,
        details=row.details,
        skill_id=row.skill_id,
        skill_name=row.skill.name_ar if row.skill else None,
        skill_slug=row.skill.slug if row.skill else None,
        location_id=row.location_id,
        location_name=row.location.name_ar if row.location else None,
        location_slug=row.location.slug if row.location else None,
        created_at=row.created_at,
        solved_at=row.solved_at,
    )


@public_router.post(
    "/service-requests", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
def send_open_service_request(
    payload: OpenServiceRequestIn, db: DbSession, settings: AppSettings, client_ip: ClientIp
) -> MessageResponse:
    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket="open_request_ip",
                limit=settings.service_request_per_ip_limit,
                window_seconds=settings.service_request_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "service_request.rate_limited")
    # Site-wide, so a sender rotating addresses still meets a ceiling.
    overall = limiter.hit(
        RateLimitRule(
            bucket="open_request_global",
            limit=settings.partner_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "service_request.rate_limited")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    if payload.skill_id is not None and db.get(TalentSkill, payload.skill_id) is None:
        raise ValidationError("talent.unknown_skill", code="unknown_skill")
    if payload.location_id is not None and db.get(Location, payload.location_id) is None:
        raise ValidationError("talent.unknown_location", code="unknown_location")

    db.add(OpenServiceRequest(**payload.model_dump(exclude={"captcha_token"})))
    db.commit()
    return MessageResponse(message=translate("open_request.received"))


@admin_router.get("/service-requests", response_model=list[OpenServiceRequestOut])
def list_open_service_requests(
    db: DbSession, admin: AdminUser, solved: Annotated[bool, Query()] = False
) -> list[OpenServiceRequestOut]:
    """Open requests, or with ``solved`` the archive; newest first."""
    stmt = select(OpenServiceRequest).options(
        joinedload(OpenServiceRequest.skill), joinedload(OpenServiceRequest.location)
    )
    if solved:
        stmt = stmt.where(OpenServiceRequest.solved_at.is_not(None))
    else:
        stmt = stmt.where(OpenServiceRequest.solved_at.is_(None))
    rows = db.execute(stmt.order_by(OpenServiceRequest.created_at.desc())).scalars()
    return [_out(row) for row in rows]


def _get(db: DbSession, request_id: uuid.UUID) -> OpenServiceRequest:
    row = db.get(OpenServiceRequest, request_id)
    if row is None:
        raise NotFoundError("open_request.not_found")
    return row


@admin_router.post(
    "/service-requests/{request_id}/solve", response_model=OpenServiceRequestOut
)
def solve_open_service_request(
    request_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> OpenServiceRequestOut:
    row = _get(db, request_id)
    if row.solved_at is None:
        row.solved_at = datetime.now(UTC)
        db.commit()
        db.refresh(row)
    return _out(row)


@admin_router.post(
    "/service-requests/{request_id}/reopen", response_model=OpenServiceRequestOut
)
def reopen_open_service_request(
    request_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> OpenServiceRequestOut:
    row = _get(db, request_id)
    if row.solved_at is not None:
        row.solved_at = None
        db.commit()
        db.refresh(row)
    return _out(row)


@admin_router.delete("/service-requests/{request_id}", response_model=MessageResponse)
def delete_open_service_request(
    request_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> MessageResponse:
    db.delete(_get(db, request_id))
    db.commit()
    return MessageResponse(message=translate("open_request.deleted"))
