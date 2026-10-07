"""The about page's team section ("meet the team"), set by an administrator."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

#: The owners asked for six photographs, each with a sentence under it. The
#: slots are fixed rather than a growing list, so the layout the page was
#: designed around is the one it always has.
TEAM_SLOTS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)


class TeamMember(Base):
    """One of the six places in the team section: a photo and a caption.

    A slot with neither is not shown; a slot with no row at all is the same.
    The caption is plain text in each language, rendered as a string.
    """

    __tablename__ = "team_members"

    slot: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
