"""Internal bug/feedback tickets — an admin-only Kanban board.

This is deliberately not user-facing: a business or talent owner never sees
this table. It replaces reporting a bug over WhatsApp with something that
keeps a history, can carry a screenshot and attachments, and can later be
picked up programmatically (an ``assignee_id`` that is a person today could
be a service account tomorrow — nothing here assumes the assignee is human).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import FeedbackAttachmentKind, FeedbackPriority, FeedbackStatus

if TYPE_CHECKING:
    from app.models.user import User


class FeedbackTicket(Base, TimestampMixin):
    """One reported bug or piece of feedback and its place on the board."""

    __tablename__ = "feedback_tickets"
    __table_args__ = (
        Index("ix_feedback_tickets_status_sort_order", "status", "sort_order"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[FeedbackStatus] = mapped_column(
        pg_enum(FeedbackStatus, "feedback_status"),
        default=FeedbackStatus.BACKLOG,
        nullable=False,
        index=True,
    )
    priority: Mapped[FeedbackPriority] = mapped_column(
        pg_enum(FeedbackPriority, "feedback_priority"),
        default=FeedbackPriority.MEDIUM,
        nullable=False,
    )

    # Where the reporter was and what their browser reported — the fastest way
    # to reproduce a bug, captured automatically rather than typed by hand.
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_context: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # The roadmap issue that serves this ticket, when one does.
    #
    # A number rather than a URL, and no foreign key: GitHub owns the issue,
    # this column only records which one. It exists so a triage agent can tell
    # which issue serves which ticket without matching on title text, which is
    # the one thing it should not be guessing at. Nullable because most
    # tickets never get an issue, and unique-less because two tickets can
    # reasonably be served by one issue.
    github_issue_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )

    # Manual order within a status column; the board writes this on every drag.
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])

    attachments: Mapped[list[FeedbackAttachment]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="FeedbackAttachment.created_at",
    )
    comments: Mapped[list[FeedbackComment]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="FeedbackComment.created_at",
    )


class FeedbackAttachment(Base):
    """Metadata for a screenshot, photo or document; bytes live in storage.

    Deliberately has no public ``url`` column, the same choice
    :class:`~app.models.verification.OwnerVerificationDocument` makes: a bug
    screenshot can easily contain the same personal data the app otherwise
    keeps out of public reach, so bytes are only ever served through the
    admin-gated download endpoint.
    """

    __tablename__ = "feedback_attachments"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[FeedbackAttachmentKind] = mapped_column(
        pg_enum(FeedbackAttachmentKind, "feedback_attachment_kind"), nullable=False
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[FeedbackTicket] = relationship(back_populates="attachments")


class FeedbackComment(Base, TimestampMixin):
    """An append-only note on a ticket — the "ticketing" half of the board."""

    __tablename__ = "feedback_comments"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped[FeedbackTicket] = relationship(back_populates="comments")
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])
