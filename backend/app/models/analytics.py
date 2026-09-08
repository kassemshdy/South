"""How often a public listing was looked at, and nothing else about who.

This table is the whole of #46. The project exists to give southern
businesses exposure, and until this landed the person being exposed could
not see the exposure: there was no per-listing counter anywhere, only
directory-wide totals for the homepage strip.

**No visitor data is stored at all.** No IP address, no cookie, no session
identifier, no user agent, no fingerprint -- one row per listing per day
holding an integer. That is a deliberate design constraint rather than an
oversight, and it has a consequence worth stating in the model itself:
without a per-visitor identifier the number is an honest count of *views*,
not of people. Every label on it must say views. An owner who works out
that the dashboard oversells one number will stop trusting all of them.

The shape follows ``RateLimitEvent`` in ``app/models/auth.py`` -- a small
append-mostly table with a composite lookup index -- but a per-day counter
is a much smaller thing than a row per view, and needs no pruning.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, pg_enum, uuid_pk
from app.models.enums import ViewSubject


class ListingViewDaily(Base):
    """One (listing, day) pair and the number of views it got.

    The unique constraint is load-bearing, not hygiene: the counter is
    written with ``INSERT ... ON CONFLICT DO UPDATE SET views = views + 1``,
    which needs it to resolve the conflict. Two simultaneous views of the
    same listing therefore serialise on the row rather than racing to
    produce two rows or losing a count.

    ``day`` is a UTC date. South Lebanon is UTC+3, so a day here turns over
    at 3am local -- immaterial to "views this week", and worth far less than
    having one definition of a day across the API, the database and the
    series the dashboard draws.
    """

    __tablename__ = "listing_view_daily"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "day",
            name="uq_listing_view_daily_subject_day",
        ),
        Index("ix_listing_view_daily_lookup", "subject_type", "subject_id", "day"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_type: Mapped[ViewSubject] = mapped_column(
        pg_enum(ViewSubject, "view_subject"), nullable=False
    )
    # No ForeignKey: this points at businesses, talent_profiles or
    # business_items depending on subject_type. See ViewSubject's docstring.
    subject_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
