"""The text of the site's static pages, written by an administrator."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

#: Every static page there is, in the order the admin screen lists them. Each
#: key is a page the frontend already has a route for; a key with no row, or
#: a field left empty, shows the page's built-in text from the locale catalog.
#: Not every key is a whole page: ``offer_eligibility`` is the "who can list in
#: the first phase" block on /offer -- its title, its list (one item per line
#: of the body) and the note under it (the summary).
PAGE_KEYS: tuple[str, ...] = ("about", "offer_eligibility")


class Page(Base):
    """One static page's title, short summary and body, in both languages.

    The body is plain text, never HTML: the page renders it as a string, so
    nothing typed here can inject markup. ``summary`` is the short version --
    the footer's «about the platform» paragraph and the page's search
    description.
    """

    __tablename__ = "pages"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    title_ar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
