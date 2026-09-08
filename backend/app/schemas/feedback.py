from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FeedbackAttachmentKind, FeedbackPriority, FeedbackStatus
from app.schemas.common import ORMModel


class FeedbackAttachmentOut(ORMModel):
    id: uuid.UUID
    kind: FeedbackAttachmentKind
    content_type: str
    original_filename: str | None = None
    size_bytes: int | None = None
    created_at: datetime


class FeedbackCommentOut(ORMModel):
    id: uuid.UUID
    body: str
    author_id: uuid.UUID | None = None
    author_display_name: str | None = None
    created_at: datetime


class FeedbackUserOut(ORMModel):
    """Just enough of a User to label a reporter, assignee, or the picker
    that assigns one — an administrator's own account details, never an
    owner's."""

    id: uuid.UUID
    display_name: str | None = None
    email: str | None = None


class FeedbackTicketSummaryOut(ORMModel):
    """Card-sized payload for the Kanban board."""

    id: uuid.UUID
    title: str
    status: FeedbackStatus
    priority: FeedbackPriority
    sort_order: int
    reporter: FeedbackUserOut
    assignee: FeedbackUserOut | None = None
    github_issue_number: int | None = None
    attachment_count: int = 0
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime


class FeedbackTicketDetailOut(FeedbackTicketSummaryOut):
    description: str | None = None
    page_path: str | None = None
    client_context: str | None = None
    resolved_at: datetime | None = None
    attachments: list[FeedbackAttachmentOut] = Field(default_factory=list)
    comments: list[FeedbackCommentOut] = Field(default_factory=list)


class FeedbackTicketCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    # Captured automatically by the reporting widget, not typed by hand.
    page_path: str | None = Field(default=None, max_length=500)
    client_context: str | None = Field(default=None, max_length=500)


class FeedbackSubmissionIn(BaseModel):
    """What a business or talent owner may report.

    Deliberately narrower than :class:`FeedbackTicketCreateIn`: there is no
    ``priority``. Asked to rank their own problem everybody reasonably answers
    "urgent", which makes the field carry no information and the board harder
    to triage -- so a reporter's ticket comes in at the default and an
    administrator decides. The widget already hides the picker; this is the
    half that cannot be bypassed by posting directly.
    """

    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    page_path: str | None = Field(default=None, max_length=500)
    client_context: str | None = Field(default=None, max_length=500)


class FeedbackSubmissionOut(ORMModel):
    """The receipt a reporter gets back.

    Just enough to attach a screenshot to what was filed. It carries none of
    the board's internal state -- status, position, assignee, or who else has
    commented -- because a reporter is not a participant in triage.
    """

    id: uuid.UUID
    title: str
    created_at: datetime


class FeedbackTicketUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: FeedbackPriority | None = None
    assignee_id: uuid.UUID | None = None
    # Explicit null unlinks. `ge=1` because GitHub numbers issues from 1, so a
    # 0 or a negative would be a caller's bug arriving as a broken link rather
    # than as an error.
    github_issue_number: int | None = Field(default=None, ge=1)


class FeedbackMoveIn(BaseModel):
    """Where a drag on the board dropped the card: which column, and at what
    position within it. The service re-derives every affected sort_order from
    this rather than trusting a client-computed order value."""

    status: FeedbackStatus
    index: int = Field(ge=0)


class FeedbackCommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
