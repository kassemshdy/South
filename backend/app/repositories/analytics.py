"""View counter data access.

Two operations and a purge. Like every repository here it makes no
authorization decision: ``series`` returns counts for whatever subject ids
it is handed, and it is the service's job to have established that the
caller owns them.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models.analytics import ListingViewDaily
from app.models.enums import ViewSubject
from app.repositories.base import BaseRepository


class ViewCounterRepository(BaseRepository[ListingViewDaily]):
    model = ListingViewDaily

    def record(
        self, subject_type: ViewSubject, subject_id: uuid.UUID, day: date
    ) -> None:
        """Add one to today's count, creating the row if this is the first.

        A plain read-then-write would lose counts whenever two people opened
        the same listing at once. ``ON CONFLICT DO UPDATE`` pushes that to
        Postgres, which serialises the two on the row: the increment is
        computed from the stored value, not from one the API read a moment
        ago and may have had overtaken.
        """
        stmt = (
            insert(ListingViewDaily)
            .values(
                id=uuid.uuid4(),
                subject_type=subject_type,
                subject_id=subject_id,
                day=day,
                views=1,
            )
            .on_conflict_do_update(
                constraint="uq_listing_view_daily_subject_day",
                set_={"views": ListingViewDaily.views + 1},
            )
        )
        self.db.execute(stmt)

    def series(
        self,
        subject_type: ViewSubject,
        subject_ids: Iterable[uuid.UUID],
        since: date,
    ) -> dict[uuid.UUID, dict[date, int]]:
        """Daily counts from ``since`` onward, keyed by subject then day.

        One query for every listing an owner has rather than one per card.
        Days with no views are simply absent -- the caller fills the gaps,
        because only the caller knows how long a window it is drawing.
        """
        ids = list(subject_ids)
        if not ids:
            return {}
        stmt = select(
            ListingViewDaily.subject_id,
            ListingViewDaily.day,
            ListingViewDaily.views,
        ).where(
            ListingViewDaily.subject_type == subject_type,
            ListingViewDaily.subject_id.in_(ids),
            ListingViewDaily.day >= since,
        )
        counts: dict[uuid.UUID, dict[date, int]] = {}
        for subject_id, day, views in self.db.execute(stmt).all():
            counts.setdefault(subject_id, {})[day] = views
        return counts

    def purge(self, subject_type: ViewSubject, subject_id: uuid.UUID) -> None:
        """Drop every counter for a listing that no longer exists.

        ``subject_id`` carries no foreign key -- it points at one of three
        tables depending on ``subject_type`` -- so nothing cascades and the
        rows have to be removed by hand when a listing is deleted.
        """
        for row in self.db.execute(
            select(ListingViewDaily).where(
                ListingViewDaily.subject_type == subject_type,
                ListingViewDaily.subject_id == subject_id,
            )
        ).scalars():
            self.db.delete(row)
        self.db.flush()
