"""Collab reels on the home page, added by an administrator.

Instagram videos the project made with the people it lists (the owners'
request, 28 Oct 2026). An administrator adds each one with a cover photo and
its link; the home page shows the cover, and opening it plays Instagram's
own embed in a pop-up. Distinct from the stories row, which is the owners'
own introduction videos on their listings.

Only the post's kind and shortcode are stored (see
``app.core.urls.instagram_post``), never the pasted link.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk


class Reel(Base, TimestampMixin):
    __tablename__ = "reels"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    instagram_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    instagram_code: Mapped[str] = mapped_column(String(40), nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
