"""Admin-only bug/feedback ticketing and its Kanban board.

Every route here depends on ``AdminUser`` — there is no owner- or
public-facing view of this feature at all, unlike the business/talent
routers which split a public surface from an owner one.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api.serializers import feedback_ticket_detail, feedback_ticket_summary, feedback_user_out
from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.i18n import translate
from app.models.enums import FeedbackAttachmentKind, UserRole
from app.models.feedback import FeedbackTicket
from app.repositories.feedback import FeedbackTicketRepository
from app.repositories.user import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.feedback import (
    FeedbackCommentIn,
    FeedbackMoveIn,
    FeedbackTicketCreateIn,
    FeedbackTicketDetailOut,
    FeedbackTicketSummaryOut,
    FeedbackTicketUpdateIn,
    FeedbackUserOut,
)
from app.services.feedback import FeedbackService
from app.services.feedback_attachments import FeedbackAttachmentService
from app.storage.factory import get_storage

router = APIRouter(prefix="/admin/feedback", tags=["admin-feedback"])


def _load(db: DbSession, ticket_id: uuid.UUID) -> FeedbackTicket:
    ticket = FeedbackTicketRepository(db).get_with_relations(ticket_id)
    if ticket is None:
        raise NotFoundError("feedback.not_found")
    return ticket


@router.get("/tickets", response_model=list[FeedbackTicketSummaryOut])
def list_tickets(db: DbSession, admin: AdminUser) -> list[FeedbackTicketSummaryOut]:
    """Every ticket, ordered for the board. There are dozens of these, not
    thousands, so unlike the business/talent directories this is unpaginated —
    the client renders the whole board in one request."""
    return [feedback_ticket_summary(t) for t in FeedbackTicketRepository(db).list_board()]


@router.get("/assignees", response_model=list[FeedbackUserOut])
def list_assignees(db: DbSession, admin: AdminUser) -> list[FeedbackUserOut]:
    """Administrators only — a ticket is never assigned to a business or
    talent owner."""
    users = UserRepository(db).list_by_role(UserRole.ADMIN)
    return [out for user in users if (out := feedback_user_out(user)) is not None]


@router.post("/tickets", response_model=FeedbackTicketDetailOut, status_code=201)
def create_ticket(
    payload: FeedbackTicketCreateIn, admin: AdminUser, db: DbSession
) -> FeedbackTicketDetailOut:
    ticket = FeedbackService(db).create(admin, payload)
    return feedback_ticket_detail(ticket)


@router.get("/tickets/{ticket_id}", response_model=FeedbackTicketDetailOut)
def get_ticket(ticket_id: uuid.UUID, db: DbSession, admin: AdminUser) -> FeedbackTicketDetailOut:
    return feedback_ticket_detail(_load(db, ticket_id))


@router.put("/tickets/{ticket_id}", response_model=FeedbackTicketDetailOut)
def update_ticket(
    ticket_id: uuid.UUID, payload: FeedbackTicketUpdateIn, db: DbSession, admin: AdminUser
) -> FeedbackTicketDetailOut:
    updated = FeedbackService(db).update(_load(db, ticket_id), payload)
    return feedback_ticket_detail(updated)


@router.delete("/tickets/{ticket_id}", response_model=MessageResponse)
def delete_ticket(
    ticket_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    ticket = _load(db, ticket_id)
    attachments = FeedbackAttachmentService(get_storage(), settings)
    for attachment in list(ticket.attachments):
        attachments.delete(db, attachment)
    FeedbackService(db).delete(ticket)
    return MessageResponse(message=translate("feedback.deleted"))


@router.post("/tickets/{ticket_id}/move", response_model=list[FeedbackTicketSummaryOut])
def move_ticket(
    ticket_id: uuid.UUID, payload: FeedbackMoveIn, db: DbSession, admin: AdminUser
) -> list[FeedbackTicketSummaryOut]:
    """Reorders the board after a drag. Returns the whole board rather than
    just the moved card, since a move can renumber cards in two columns."""
    FeedbackService(db).move(_load(db, ticket_id), payload)
    return [feedback_ticket_summary(t) for t in FeedbackTicketRepository(db).list_board()]


@router.post("/tickets/{ticket_id}/comments", response_model=FeedbackTicketDetailOut)
def add_comment(
    ticket_id: uuid.UUID, payload: FeedbackCommentIn, db: DbSession, admin: AdminUser
) -> FeedbackTicketDetailOut:
    updated = FeedbackService(db).add_comment(_load(db, ticket_id), admin, payload.body)
    return feedback_ticket_detail(updated)


@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=FeedbackTicketDetailOut,
    status_code=201,
)
def upload_attachment(
    ticket_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Screenshot, photo, or document")],
    kind: Annotated[FeedbackAttachmentKind, Form()] = FeedbackAttachmentKind.PHOTO,
) -> FeedbackTicketDetailOut:
    ticket = _load(db, ticket_id)
    data = file.file.read()
    if len(data) > settings.max_feedback_attachment_bytes:
        raise PayloadTooLargeError()

    FeedbackAttachmentService(get_storage(), settings).store(
        db=db,
        ticket=ticket,
        data=data,
        kind=kind,
        original_filename=file.filename,
    )
    return feedback_ticket_detail(_load(db, ticket_id))


@router.delete(
    "/tickets/{ticket_id}/attachments/{attachment_id}", response_model=FeedbackTicketDetailOut
)
def delete_attachment(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> FeedbackTicketDetailOut:
    ticket = _load(db, ticket_id)
    attachment = next((a for a in ticket.attachments if a.id == attachment_id), None)
    if attachment is None:
        raise NotFoundError("feedback.attachment_not_found")
    FeedbackAttachmentService(get_storage(), settings).delete(db, attachment)
    return feedback_ticket_detail(_load(db, ticket_id))


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}/download")
def download_attachment(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> Response:
    ticket = _load(db, ticket_id)
    attachment = next((a for a in ticket.attachments if a.id == attachment_id), None)
    if attachment is None:
        raise NotFoundError("feedback.attachment_not_found")
    data = FeedbackAttachmentService(get_storage(), settings).read_bytes(attachment)
    filename = attachment.original_filename or f"{attachment.id}"
    # Inline rather than attachment: images and PDFs render in a preview panel
    # on the board rather than forcing a download dialog every time.
    return Response(
        content=data,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
