"""Product/service data access, including the public search query.

Mirrors ``BusinessRepository``: :meth:`public_query` is the single enforcement
point for what an anonymous visitor may see — a product is visible only when
its parent business is approved *and* the item itself is available.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import Select, func, nullslast, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.arabic import normalize_arabic
from app.core.pagination import Page
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.repositories.base import BaseRepository

SortOption = Literal["newest", "name", "oldest", "price_asc", "price_desc"]


class ItemRepository(BaseRepository[BusinessItem]):
    model = BusinessItem

    # --- Loading -----------------------------------------------------------

    def _with_relations(self, stmt: Select[tuple[BusinessItem]]) -> Select[tuple[BusinessItem]]:
        return stmt.options(
            joinedload(BusinessItem.business).joinedload(Business.category),
            joinedload(BusinessItem.business)
            .joinedload(Business.location)
            .joinedload(Location.parent),
        )

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(BusinessItem.id).where(BusinessItem.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(BusinessItem.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    # --- Querying ----------------------------------------------------------

    def public_query(self) -> Select[tuple[BusinessItem]]:
        """Base statement for everything a visitor is allowed to see."""
        return (
            select(BusinessItem)
            .join(Business, BusinessItem.business_id == Business.id)
            .where(Business.status == BusinessStatus.APPROVED, BusinessItem.is_available.is_(True))
        )

    def get_by_slug(self, slug: str) -> BusinessItem | None:
        stmt = self._with_relations(self.public_query().where(BusinessItem.slug == slug))
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def public_by_ids(
        self, business_id: uuid.UUID, item_ids: Sequence[uuid.UUID]
    ) -> list[BusinessItem]:
        """Items a visitor may order: publicly visible *and* on this listing.

        Built on ``public_query`` so "what a visitor may see" keeps one
        definition. Both halves matter -- without the business_id an order
        could name another shop's product, and without public_query it could
        name an unavailable one or one belonging to a listing that is not
        approved.
        """
        ids = list(item_ids)
        if not ids:
            return []
        stmt = self.public_query().where(
            BusinessItem.business_id == business_id, BusinessItem.id.in_(ids)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def public_product_count(self) -> int:
        """How many products a visitor can actually reach.

        Built on ``public_query`` like everything else here, so the number on
        the homepage counts exactly the rows the directory would list — an
        unavailable item, or one belonging to a listing that is not approved,
        is not advertised in a total a visitor cannot then find.
        """
        return self.db.execute(
            select(func.count()).select_from(self.public_query().subquery())
        ).scalar_one()

    def public_slugs(self) -> list[tuple[str, object]]:
        """(slug, updated_at) pairs for the sitemap.

        Built on ``public_query`` rather than its own WHERE clause: the rule
        for what a visitor may see lives in one place, so a product that is
        unavailable or whose business is not approved cannot be advertised to
        a crawler by a predicate that drifted.
        """
        # Columns come off the subquery itself. Selecting
        # ``BusinessItem.slug`` while merely adding the subquery to FROM is a
        # cartesian product, which SQLAlchemy warns about and which quietly
        # multiplied every product by every other one.
        public = self.public_query().subquery()
        rows = self.db.execute(
            select(public.c.slug, public.c.updated_at).order_by(public.c.updated_at.desc())
        ).all()
        return [(row[0], row[1]) for row in rows]

    def _apply_filters(
        self,
        stmt: Select[tuple[BusinessItem]],
        *,
        q: str | None,
        category_slug: str | None,
        location_slug: str | None,
    ) -> Select[tuple[BusinessItem]]:
        if category_slug:
            stmt = stmt.join(Category, Business.category_id == Category.id).where(
                Category.slug == category_slug
            )

        if location_slug:
            # Matching a district also matches the towns beneath it, same as
            # BusinessRepository._apply_filters.
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
            stmt = stmt.where(BusinessItem.search_text.like(needle))

        return stmt

    def _apply_sort(
        self, stmt: Select[tuple[BusinessItem]], sort: SortOption
    ) -> Select[tuple[BusinessItem]]:
        """Order the results, including the two price orders.

        **A product with no stated price sorts last in both directions.**
        Postgres would otherwise put NULLs first on a descending order, so
        "most expensive first" would open with the products that name no
        price at all -- which reads as a broken page, and is also a claim the
        data does not support: a blank price is an unanswered question, not a
        high or a low one. ``nullslast`` says that once, for both directions.

        **The comparison is on the stored number, across currencies.** Every
        listing here is priced in dollars today, so this is exact; the moment
        one is priced in lira, 100,000 LBP would sort above $100 while being
        worth a fraction of it. There is no exchange rate in this directory
        and a hardcoded one would go stale silently, so the honest fix when
        that day comes is to convert at read time from a rate someone
        maintains -- not to leave this comparing two different units.
        """
        if sort == "name":
            return stmt.order_by(BusinessItem.title.asc())
        if sort == "oldest":
            return stmt.order_by(BusinessItem.created_at.asc())
        if sort == "price_asc":
            return stmt.order_by(nullslast(BusinessItem.price.asc()), BusinessItem.id.asc())
        if sort == "price_desc":
            return stmt.order_by(nullslast(BusinessItem.price.desc()), BusinessItem.id.asc())
        return stmt.order_by(BusinessItem.created_at.desc())

    def search_public(
        self,
        *,
        q: str | None = None,
        category_slug: str | None = None,
        location_slug: str | None = None,
        sort: SortOption = "newest",
        page: int = 1,
        page_size: int = 12,
    ) -> Page[BusinessItem]:
        """Paginated public search. Never returns an unreachable product."""
        filtered = self._apply_filters(
            self.public_query(),
            q=q,
            category_slug=category_slug,
            location_slug=location_slug,
        )

        total = int(
            self.db.execute(select(func.count()).select_from(filtered.subquery())).scalar_one()
        )

        stmt = self._apply_sort(self._with_relations(filtered), sort)
        rows = (
            self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
            .unique()
            .scalars()
            .all()
        )
        return Page(items=list(rows), total=total, page=page, page_size=page_size)


def make_repository(db: Session) -> ItemRepository:
    return ItemRepository(db)
