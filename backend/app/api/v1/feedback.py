"""Owner-facing bug reporting.

Two routes and no more. An owner may report a problem and attach a screenshot
of it; everything else about the board -- reading it, triaging it, commenting,
assigning, moving a card, deleting -- stays under ``/api/admin/feedback``
behind ``AdminUser``.

The split exists because reporting and triaging are different jobs with
different audiences, and the reporter's half must not leak the other. Reading
a ticket back would show an owner the board's internal state and, on a ticket
raised by an administrator, a colleague's notes about someone else's listing.
So a submission returns only a receipt.

The attachment route is scoped to the reporter, not merely to a signed-in
account: a screenshot lives under the ticket it belongs to, and a ticket id
appearing in a request is never on its own evidence that the caller filed it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.api.serializers import feedback_submission
from app.core.dependencies import AppSettings, CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models.enums import FeedbackAttachmentKind
from app.models.feedback import FeedbackTicket
from app.repositories.feedback import FeedbackTicketRepository
from app.schemas.feedback import FeedbackSubmissionIn, FeedbackSubmissionOut
from app.services.feedback import FeedbackService
from app.services.feedback_attachments import FeedbackAttachmentService
from app.storage.factory import get_storage

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _own_ticket(db: DbSession, ticket_id: uuid.UUID, user: CurrentUser) -> FeedbackTicket:
    """Load a ticket the caller reported.

    404 rather than 403 for someone else's ticket, the same choice
    ``require_owned_business`` makes: the response must not confirm that an id
    exists to an account that has no business with it.
    """
    ticket = FeedbackTicketRepository(db).get_for_reporter(ticket_id, user.id)
    if ticket is None:
        raise NotFoundError("feedback.not_found")
    return ticket


@router.post("", response_model=FeedbackSubmissionOut, status_code=201)
def submit_feedback(
    payload: FeedbackSubmissionIn, user: CurrentUser, db: DbSession
) -> FeedbackSubmissionOut:
    """Report a problem. Any signed-in account may; an administrator raising a
    ticket for triage uses the admin route, which also accepts a priority."""
    ticket = FeedbackService(db).submit(user, payload)
    return feedback_submission(ticket)


@router.post("/{ticket_id}/attachments", response_model=FeedbackSubmissionOut, status_code=201)
def attach_to_own_report(
    ticket_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Screenshot or photo of the problem")],
    kind: Annotated[FeedbackAttachmentKind, Form()] = FeedbackAttachmentKind.SCREENSHOT,
) -> FeedbackSubmissionOut:
    ticket = _own_ticket(db, ticket_id, user)
    FeedbackAttachmentService(get_storage(), settings).store(
        db=db,
        ticket=ticket,
        data=file.file.read(),
        kind=kind,
        original_filename=file.filename,
    )
    return feedback_submission(ticket)
