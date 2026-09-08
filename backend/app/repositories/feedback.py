"""Feedback ticket data access.

Unlike the business/talent repositories, there is no public/private split
here — every route this repository serves already sits behind ``AdminUser``,
so there is no ``public_query`` to enforce.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.enums import FeedbackStatus
from app.models.feedback import FeedbackComment, FeedbackTicket
from app.repositories.base import BaseRepository


class FeedbackTicketRepository(BaseRepository[FeedbackTicket]):
    model = FeedbackTicket

    def _with_relations(
        self, stmt: Select[tuple[FeedbackTicket]]
    ) -> Select[tuple[FeedbackTicket]]:
        return stmt.options(
            joinedload(FeedbackTicket.reporter),
            joinedload(FeedbackTicket.assignee),
            selectinload(FeedbackTicket.attachments),
            selectinload(FeedbackTicket.comments).joinedload(FeedbackComment.author),
        ).execution_options(populate_existing=True)
        # populate_existing: every mutation (an attachment/comment add, an
        # assignee change) reloads the same already-in-session ticket object
        # by primary key. Without this, SQLAlchemy's identity map returns
        # that object as-is and skips re-running the eager loaders above,
        # so the relationship collections it just changed would read back
        # stale — the fresh query would silently be a no-op for them.

    def get_with_relations(self, ticket_id: uuid.UUID) -> FeedbackTicket | None:
        return self.db.execute(
            self._with_relations(select(FeedbackTicket).where(FeedbackTicket.id == ticket_id))
        ).unique().scalar_one_or_none()

    def get_for_reporter(
        self, ticket_id: uuid.UUID, reporter_id: uuid.UUID
    ) -> FeedbackTicket | None:
        """A ticket the given account reported, or None.

        Scoped by reporter rather than looked up by id alone, the same way the
        business repository scopes an owner's listing: the id in the request is
        never enough on its own.
        """
        return self.db.execute(
            self._with_relations(
                select(FeedbackTicket).where(
                    FeedbackTicket.id == ticket_id,
                    FeedbackTicket.reporter_id == reporter_id,
                )
            )
        ).unique().scalar_one_or_none()

    def list_board(self) -> list[FeedbackTicket]:
        """Every ticket, ordered the way the board renders a column."""
        stmt = self._with_relations(select(FeedbackTicket)).order_by(
            FeedbackTicket.status, FeedbackTicket.sort_order
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_in_status(self, status: FeedbackStatus) -> list[FeedbackTicket]:
        stmt = (
            select(FeedbackTicket)
            .where(FeedbackTicket.status == status)
            .order_by(FeedbackTicket.sort_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    def next_sort_order(self, status: FeedbackStatus) -> int:
        current_max = self.db.execute(
            select(func.max(FeedbackTicket.sort_order)).where(FeedbackTicket.status == status)
        ).scalar_one()
        return (current_max + 1) if current_max is not None else 0

    def count_by_status(self) -> dict[FeedbackStatus, int]:
        rows = self.db.execute(
            select(FeedbackTicket.status, func.count()).group_by(FeedbackTicket.status)
        ).all()
        return {row[0]: row[1] for row in rows}


def make_repository(db: Session) -> FeedbackTicketRepository:
    return FeedbackTicketRepository(db)
