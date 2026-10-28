"""Short videos shown on the home page, chosen by an administrator.

A reel is a link to a YouTube Short or an Instagram post, not a copy of it:
the video stays where it is and the page embeds that site's own player.
What is kept here is the video's kind (``youtube``, or Instagram's ``reel``,
``p`` or ``tv``) and its id or code, a caption in each language, an optional
cover photograph for the card, and whether and where it is shown.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk


class Reel(Base, TimestampMixin):
    __tablename__ = "reels"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    shortcode: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    caption_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Lowest first; a new reel goes in front of the others.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
