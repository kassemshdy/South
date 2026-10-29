"""A message from the floating "ask us" button: feedback or any question.

Anyone may send one, signed in or not, from any public page. Like a partner
request it carries a stranger's name and a way to reach them, so it is read
by administrators only: no public route reads it, and nothing about it is
published.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk


class ContactMessage(Base, TimestampMixin):
    __tablename__ = "contact_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # At least one way to answer is required, but neither on its own: some
    # people would rather give an email than a number.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    # feedback / question / other -- see ``ContactTopic``.
    topic: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # The page they were on when they asked, path only.
    page_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Set when an administrator marks it solved: archived, not deleted.
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
