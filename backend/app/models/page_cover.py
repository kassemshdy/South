"""The photograph at the top of a public page, chosen by an administrator."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

#: The pages that carry a cover, keyed by a stable name rather than a URL so
#: a route can move without losing its photograph. Order is the order the
#: admin screen lists them in. A page with no row shows the site's default.
PAGE_COVER_KEYS: tuple[str, ...] = (
    "home",
    "offer",
    "browse",
    "products",
    "products_local",
    "products_imported",
    "talent",
)


class PageCover(Base):
    """One page's cover, replacing the default photograph.

    Asked for so the photographs on the site can change without a deploy:
    an administrator uploads one per page, and removing it returns the page
    to the default. Only the stored image is kept -- it goes through the same
    pipeline as every other upload (decoded, re-encoded, EXIF stripped).
    """

    __tablename__ = "page_covers"

    page_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
