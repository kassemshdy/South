"""Counting views of a public listing, and reporting them to its owner.

The whole point of #46 is one sentence on a dashboard -- "23 people looked
at your page this week" -- and two rules make that sentence honest:

1. **The owner's own views do not count.** An owner refreshing their own
   page must not inflate their numbers, or the one trustworthy signal on
   the dashboard becomes a lie. We know who the caller is whenever they are
   signed in, so this costs nothing.
2. **It is called views, never visitors.** Nothing identifying a visitor is
   stored, so the number cannot be a count of people and must not be
   labelled as one.

Recording is deliberately **best effort**: a failed counter write is logged
and swallowed rather than turned into a 500. A public listing page is worth
more than one increment of an analytics counter, and this runs on the read
path of every public profile in the directory.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.enums import ViewSubject
from app.models.user import User
from app.repositories.analytics import ViewCounterRepository
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository

logger = logging.getLogger(__name__)

# Two windows, both shown: a fortnight is enough to draw a shape from, and
# a week is the span the dashboard sentence talks about.
WINDOW_DAYS = 14
RECENT_DAYS = 7


@dataclass(frozen=True)
class ListingViews:
    """One listing's numbers, already gap-filled over the whole window."""

    subject_type: ViewSubject
    subject_id: uuid.UUID
    views_recent: int
    views_window: int
    series: list[int]
    series_start: date


def _today() -> date:
    """Today in UTC.

    South Lebanon is UTC+3, so a day here turns over at 3am local. That is
    immaterial to "views this week" and buys one definition of a day shared
    by the database, the API and the series the dashboard draws.
    """
    return datetime.now(UTC).date()


class ViewCounterService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ViewCounterRepository(db)

    # --- Recording ---------------------------------------------------------

    def record(
        self,
        subject_type: ViewSubject,
        subject_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        viewer: User | None,
    ) -> None:
        """Count one view, unless the viewer is the listing's own owner."""
        if viewer is not None and viewer.id == owner_id:
            return
        try:
            self._repo.record(subject_type, subject_id, _today())
            self._db.commit()
        except SQLAlchemyError:
            # Never fail a public page over a counter. Logged rather than
            # silent, so a counter that has stopped working is discoverable
            # instead of just reading as "nobody visited".
            self._db.rollback()
            logger.warning(
                "View counter write failed",
                exc_info=True,
                extra={"subject_type": subject_type.value, "subject_id": str(subject_id)},
            )

    def forget(self, subject_type: ViewSubject, subject_id: uuid.UUID) -> None:
        """Drop a deleted listing's counters. Nothing cascades to them."""
        self._repo.purge(subject_type, subject_id)

    # --- Reporting ---------------------------------------------------------

    def for_owner(self, owner: User) -> list[ListingViews]:
        """Every listing the caller owns, with its window of daily counts.

        Ownership is established here, from the authenticated user, and the
        subject ids handed to the repository are the ones that came back
        from that lookup -- never an id supplied by the request. That is why
        this endpoint needs no per-listing permission check.

        Products are counted (see the public product route) but not reported
        here: nothing surfaces them yet, and views cannot be backfilled, so
        the history is being accumulated now for when something does.
        """
        businesses = BusinessRepository(self._db).list_for_owner(owner.id)
        profile = TalentRepository(self._db).get_for_owner(owner.id)

        start = _today() - timedelta(days=WINDOW_DAYS - 1)
        results: list[ListingViews] = []

        business_counts = self._repo.series(
            ViewSubject.BUSINESS, [b.id for b in businesses], start
        )
        for business in businesses:
            results.append(
                self._assemble(
                    ViewSubject.BUSINESS,
                    business.id,
                    business_counts.get(business.id, {}),
                    start,
                )
            )

        if profile is not None:
            talent_counts = self._repo.series(ViewSubject.TALENT, [profile.id], start)
            results.append(
                self._assemble(
                    ViewSubject.TALENT,
                    profile.id,
                    talent_counts.get(profile.id, {}),
                    start,
                )
            )
        return results

    @staticmethod
    def _assemble(
        subject_type: ViewSubject,
        subject_id: uuid.UUID,
        counts: dict[date, int],
        start: date,
    ) -> ListingViews:
        """Turn sparse rows into a dense series the width of the window.

        A sparkline needs a value for every day, including the zeroes -- a
        series that silently omits quiet days draws a misleading shape.
        """
        days: Sequence[date] = [start + timedelta(days=offset) for offset in range(WINDOW_DAYS)]
        series = [counts.get(day, 0) for day in days]
        return ListingViews(
            subject_type=subject_type,
            subject_id=subject_id,
            views_recent=sum(series[-RECENT_DAYS:]),
            views_window=sum(series),
            series=series,
            series_start=start,
        )
