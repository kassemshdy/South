"""Feedback ticket lifecycle: create, edit, move across the board, comment.

A ticket is raised by an administrator or reported by an owner, and either
way only administrators ever see the board. There is no moderation state
machine as in :mod:`app.services.moderation`, because nothing here is
published -- but a reporter's submission still goes through ``submit`` rather
than ``create``, so what an owner may set is decided here and not by the
shape of a request.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.enums import FeedbackStatus, UserRole
from app.models.feedback import FeedbackComment, FeedbackTicket
from app.models.user import User
from app.repositories.feedback import FeedbackTicketRepository
from app.repositories.user import UserRepository
from app.schemas.feedback import (
    FeedbackMoveIn,
    FeedbackSubmissionIn,
    FeedbackTicketCreateIn,
    FeedbackTicketUpdateIn,
)

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = FeedbackTicketRepository(db)
        self._users = UserRepository(db)

    def create(self, reporter: User, payload: FeedbackTicketCreateIn) -> FeedbackTicket:
        ticket = FeedbackTicket(
            reporter_id=reporter.id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            page_path=payload.page_path,
            client_context=payload.client_context,
            status=FeedbackStatus.BACKLOG,
            sort_order=self._repo.next_sort_order(FeedbackStatus.BACKLOG),
        )
        self._repo.add(ticket)
        self._db.commit()
        logger.info(
            "Feedback ticket created",
            extra={"ticket_id": str(ticket.id), "reporter_id": str(reporter.id)},
        )
        return self._reload(ticket.id)

    def submit(self, reporter: User, payload: FeedbackSubmissionIn) -> FeedbackTicket:
        """A ticket reported by an owner rather than raised by an admin.

        Routed through the same creation path so a reported bug and a raised
        one are the same row on the same board. The priority is set here and
        not taken from the request: the decision that a reporter does not rank
        their own problem belongs in the service, where posting directly to
        the API cannot get around it.
        """
        return self.create(
            reporter,
            FeedbackTicketCreateIn(
                title=payload.title,
                description=payload.description,
                page_path=payload.page_path,
                client_context=payload.client_context,
            ),
        )

    def update(self, ticket: FeedbackTicket, payload: FeedbackTicketUpdateIn) -> FeedbackTicket:
        data = payload.model_dump(exclude_unset=True)
        if "assignee_id" in data and data["assignee_id"] is not None:
            self._validate_assignee(data["assignee_id"])
        for field, value in data.items():
            setattr(ticket, field, value)
        self._db.commit()
        return self._reload(ticket.id)

    def delete(self, ticket: FeedbackTicket) -> None:
        # Attachment bytes are removed by the caller, which holds the storage
        # backend; the rows themselves cascade at the database level.
        ticket_id = ticket.id
        self._repo.delete(ticket)
        self._db.commit()
        logger.info("Feedback ticket deleted", extra={"ticket_id": str(ticket_id)})

    def move(self, ticket: FeedbackTicket, payload: FeedbackMoveIn) -> FeedbackTicket:
        """Reorder the board to match where a drag dropped ``ticket``.

        Every sort_order in both the origin and destination column is
        re-derived from the resulting list order, rather than trusting a
        client-computed number — the same reason talent/business slugs are
        server-derived rather than client-supplied.
        """
        origin_status = ticket.status

        destination = [
            row for row in self._repo.list_in_status(payload.status) if row.id != ticket.id
        ]
        index = max(0, min(payload.index, len(destination)))
        destination.insert(index, ticket)

        ticket.status = payload.status
        now = datetime.now(UTC)
        if payload.status is FeedbackStatus.DONE and origin_status is not FeedbackStatus.DONE:
            ticket.resolved_at = now
        elif payload.status is not FeedbackStatus.DONE:
            ticket.resolved_at = None

        for position, row in enumerate(destination):
            row.sort_order = position
        self._db.flush()

        if origin_status is not payload.status:
            origin = self._repo.list_in_status(origin_status)
            for position, row in enumerate(origin):
                row.sort_order = position

        self._db.commit()
        return self._reload(ticket.id)

    def add_comment(self, ticket: FeedbackTicket, author: User, body: str) -> FeedbackTicket:
        self._db.add(FeedbackComment(ticket_id=ticket.id, author_id=author.id, body=body))
        self._db.commit()
        return self._reload(ticket.id)

    # --- internals ---------------------------------------------------------

    def _validate_assignee(self, assignee_id: uuid.UUID) -> None:
        """A ticket is only ever assigned to an administrator — the picker
        that offers this id only lists admins, but a request that supplies
        one directly must still be checked, the same way business/talent
        services validate a taxonomy id rather than letting a bad FK surface
        as an unhandled database error."""
        assignee = self._users.get(assignee_id)
        if assignee is None or assignee.role is not UserRole.ADMIN:
            raise ValidationError("feedback.unknown_assignee", code="unknown_assignee")

    def _reload(self, ticket_id: uuid.UUID) -> FeedbackTicket:
        ticket = self._repo.get_with_relations(ticket_id)
        if ticket is None:  # pragma: no cover - only on concurrent deletion
            raise NotFoundError("feedback.not_found")
        return ticket
