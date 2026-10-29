"""The floating contact form: anyone may write, only an administrator reads.

Feedback or any question, from any public page, signed in or not. Anonymous
like the partner form, so behind the same guards -- a per-address limit, a
site-wide one, and the captcha when one is configured -- and the public
route only ever writes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.errors import NotFoundError, RateLimitedError, ValidationError
from app.core.i18n import translate
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.contact import ContactMessage
from app.schemas.common import MessageResponse
from app.schemas.contact import ContactMessageIn, ContactMessageOut

public_router = APIRouter(tags=["contact"])
admin_router = APIRouter(prefix="/admin", tags=["admin-contact"])


@public_router.post(
    "/contact-messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
def send_contact_message(
    payload: ContactMessageIn, db: DbSession, settings: AppSettings, client_ip: ClientIp
) -> MessageResponse:
    if not payload.phone and not payload.email:
        raise ValidationError("contact.reach_required", code="contact_reach_required")
    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket="contact_ip",
                limit=settings.contact_per_ip_limit,
                window_seconds=settings.contact_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "contact.rate_limited")
    # Site-wide, so a sender rotating addresses still meets a ceiling.
    overall = limiter.hit(
        RateLimitRule(
            bucket="contact_global",
            limit=settings.contact_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "contact.rate_limited")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    db.add(ContactMessage(**payload.model_dump(exclude={"captcha_token"})))
    db.commit()
    return MessageResponse(message=translate("contact.received"))


@admin_router.get("/contact-messages", response_model=list[ContactMessageOut])
def list_contact_messages(
    db: DbSession, admin: AdminUser, solved: Annotated[bool, Query()] = False
) -> list[ContactMessageOut]:
    """Open messages, or with ``solved`` the archive; newest first."""
    stmt = select(ContactMessage)
    if solved:
        stmt = stmt.where(ContactMessage.solved_at.is_not(None))
    else:
        stmt = stmt.where(ContactMessage.solved_at.is_(None))
    rows = db.execute(stmt.order_by(ContactMessage.created_at.desc())).scalars()
    return [ContactMessageOut.model_validate(row) for row in rows]


def _get(db: DbSession, message_id: uuid.UUID) -> ContactMessage:
    row = db.get(ContactMessage, message_id)
    if row is None:
        raise NotFoundError("contact.not_found")
    return row


@admin_router.post("/contact-messages/{message_id}/solve", response_model=ContactMessageOut)
def solve_contact_message(
    message_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> ContactMessageOut:
    """Move a handled message to the archive, keeping it."""
    row = _get(db, message_id)
    if row.solved_at is None:
        row.solved_at = datetime.now(UTC)
        db.commit()
        db.refresh(row)
    return ContactMessageOut.model_validate(row)


@admin_router.post("/contact-messages/{message_id}/reopen", response_model=ContactMessageOut)
def reopen_contact_message(
    message_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> ContactMessageOut:
    """Bring an archived message back, for one marked solved by mistake."""
    row = _get(db, message_id)
    if row.solved_at is not None:
        row.solved_at = None
        db.commit()
        db.refresh(row)
    return ContactMessageOut.model_validate(row)


@admin_router.delete("/contact-messages/{message_id}", response_model=MessageResponse)
def delete_contact_message(
    message_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> MessageResponse:
    db.delete(_get(db, message_id))
    db.commit()
    return MessageResponse(message=translate("contact.deleted"))
