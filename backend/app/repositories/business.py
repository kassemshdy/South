"""Business data access, including the public search query.

The public/private split lives here: :meth:`public_query` is the *only* place
that decides what an anonymous visitor may see, so the "APPROVED only" rule has
exactly one enforcement point.
"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.arabic import normalize_arabic
from app.core.pagination import Page
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.repositories.base import BaseRepository

SortOption = Literal["newest", "name", "oldest"]


class BusinessRepository(BaseRepository[Business]):
    model = Business

    # --- Loading -----------------------------------------------------------

    def _with_relations(self, stmt: Select[tuple[Business]]) -> Select[tuple[Business]]:
        return stmt.options(
            joinedload(Business.category),
            joinedload(Business.location).joinedload(Location.parent),
            selectinload(Business.images),
            selectinload(Business.social_links),
            selectinload(Business.items),
        )

    def get_with_relations(self, business_id: uuid.UUID) -> Business | None:
        return self.db.execute(
            self._with_relations(select(Business).where(Business.id == business_id))
        ).unique().scalar_one_or_none()

    def get_by_slug(self, slug: str, *, public_only: bool = True) -> Business | None:
        stmt = self._with_relations(select(Business).where(Business.slug == slug))
        if public_only:
            stmt = stmt.where(Business.status == BusinessStatus.APPROVED)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Business.id).where(Business.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Business.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def list_for_owner(self, owner_id: uuid.UUID) -> list[Business]:
        stmt = self._with_relations(
            select(Business)
            .where(Business.owner_id == owner_id)
            .order_by(Business.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    # --- Querying ----------------------------------------------------------

    def public_query(self) -> Select[tuple[Business]]:
        """Base statement for everything a visitor is allowed to see."""
        return select(Business).where(Business.status == BusinessStatus.APPROVED)

    def _apply_filters(
        self,
        stmt: Select[tuple[Business]],
        *,
        q: str | None,
        category_slug: str | None,
        location_slug: str | None,
    ) -> Select[tuple[Business]]:
        if category_slug:
            stmt = stmt.join(Category, Business.category_id == Category.id).where(
                Category.slug == category_slug
            )

        if location_slug:
            # Matching a district also matches the towns beneath it, so
            # filtering by "صور" returns businesses in its villages too.
            parent = select(Location.id).where(Location.slug == location_slug).scalar_subquery()
            stmt = stmt.where(
                or_(
                    Business.location_id.in_(
                        select(Location.id).where(Location.slug == location_slug)
                    ),
                    Business.location_id.in_(
                        select(Location.id).where(Location.parent_id.in_(parent))
                    ),
                )
            )

        if q:
            needle = f"%{normalize_arabic(q)}%"
            item_match = exists().where(
                BusinessItem.business_id == Business.id,
                func.lower(BusinessItem.title).like(needle),
            )
            stmt = stmt.where(or_(Business.search_text.like(needle), item_match))

        return stmt

    def _apply_sort(
        self, stmt: Select[tuple[Business]], sort: SortOption
    ) -> Select[tuple[Business]]:
        if sort == "name":
            return stmt.order_by(Business.name.asc())
        if sort == "oldest":
            return stmt.order_by(Business.created_at.asc())
        return stmt.order_by(Business.created_at.desc())

    def search_public(
        self,
        *,
        q: str | None = None,
        category_slug: str | None = None,
        location_slug: str | None = None,
        sort: SortOption = "newest",
        page: int = 1,
        page_size: int = 12,
    ) -> Page[Business]:
        """Paginated public search. Never returns a non-APPROVED business."""
        filtered = self._apply_filters(
            self.public_query(), q=q, category_slug=category_slug, location_slug=location_slug
        )

        total = int(
            self.db.execute(
                select(func.count()).select_from(filtered.subquery())
            ).scalar_one()
        )

        stmt = self._apply_sort(self._with_relations(filtered), sort)
        rows = (
            self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
            .unique()
            .scalars()
            .all()
        )
        return Page(items=list(rows), total=total, page=page, page_size=page_size)

    def list_for_admin(
        self,
        *,
        status: BusinessStatus | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[Business]:
        stmt = select(Business)
        if status is not None:
            stmt = stmt.where(Business.status == status)
        if q:
            stmt = stmt.where(Business.search_text.like(f"%{normalize_arabic(q)}%"))

        total = int(
            self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        )

        # Oldest pending first: the review queue should be FIFO.
        order = (
            Business.submitted_at.asc()
            if status is BusinessStatus.PENDING_REVIEW
            else Business.created_at.desc()
        )
        rows = (
            self.db.execute(
                self._with_relations(stmt)
                .options(joinedload(Business.owner))
                .order_by(order)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return Page(items=list(rows), total=total, page=page, page_size=page_size)

    def get_for_admin(self, business_id: uuid.UUID) -> Business | None:
        stmt = (
            self._with_relations(select(Business).where(Business.id == business_id))
            .options(
                joinedload(Business.owner),
                selectinload(Business.moderation_actions),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    # --- Aggregates --------------------------------------------------------

    def count_by_status(self) -> dict[BusinessStatus, int]:
        rows = self.db.execute(
            select(Business.status, func.count()).group_by(Business.status)
        ).all()
        return {row[0]: row[1] for row in rows}

    def approved_slugs(self) -> list[tuple[str, object]]:
        """(slug, updated_at) pairs for the sitemap — APPROVED only."""
        rows = self.db.execute(
            select(Business.slug, Business.updated_at)
            .where(Business.status == BusinessStatus.APPROVED)
            .order_by(Business.updated_at.desc())
        ).all()
        return [(row[0], row[1]) for row in rows]

    def recently_approved(self, limit: int = 8) -> list[Business]:
        stmt = self._with_relations(
            self.public_query().order_by(
                func.coalesce(Business.approved_at, Business.created_at).desc()
            )
        )
        return list(self.db.execute(stmt.limit(limit)).unique().scalars().all())

    def public_counts_by_category(self) -> dict[uuid.UUID, int]:
        rows = self.db.execute(
            select(Business.category_id, func.count())
            .where(Business.status == BusinessStatus.APPROVED)
            .group_by(Business.category_id)
        ).all()
        return {row[0]: row[1] for row in rows if row[0] is not None}

    def public_counts_by_location(self) -> dict[uuid.UUID, int]:
        rows = self.db.execute(
            select(Business.location_id, func.count())
            .where(Business.status == BusinessStatus.APPROVED)
            .group_by(Business.location_id)
        ).all()
        return {row[0]: row[1] for row in rows if row[0] is not None}


def make_repository(db: Session) -> BusinessRepository:
    return BusinessRepository(db)
