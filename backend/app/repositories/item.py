"""Product/service data access, including the public search query.

Mirrors ``BusinessRepository``: :meth:`public_query` is the single enforcement
point for what an anonymous visitor may see — a product is visible only when
its parent business is approved *and* the item itself is available.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Literal

from sqlalchemy import Select, case, func, nullslast, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.arabic import normalize_arabic
from app.core.pagination import Page
from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, GoodsOrigin, ViewSubject
from app.models.order import Order, OrderLine
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.geo import Point, nearest_first

SortOption = Literal[
    "newest", "name", "oldest", "price_asc", "price_desc", "nearest", "rating"
]


class ItemRepository(BaseRepository[BusinessItem]):
    model = BusinessItem

    # --- Loading -----------------------------------------------------------

    def _with_relations(self, stmt: Select[tuple[BusinessItem]]) -> Select[tuple[BusinessItem]]:
        return stmt.options(
            joinedload(BusinessItem.business).joinedload(Business.category),
            joinedload(BusinessItem.business)
            .joinedload(Business.location)
            .joinedload(Location.parent),
            joinedload(BusinessItem.business).joinedload(Business.owner),
        )

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(BusinessItem.id).where(BusinessItem.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(BusinessItem.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    # --- Querying ----------------------------------------------------------

    def public_query(self) -> Select[tuple[BusinessItem]]:
        """Base statement for everything a visitor is allowed to see.

        A product with no photo is not one of them (the owners' decision: the
        photo is mandatory). The form refuses to save one, but a product saved
        before that rule, or one whose upload failed, stays with its owner
        until it has a photo rather than reaching the catalogue without one.
        """
        return (
            select(BusinessItem)
            .join(Business, BusinessItem.business_id == Business.id)
            .where(
                Business.status == BusinessStatus.APPROVED,
                BusinessItem.is_available.is_(True),
                BusinessItem.image_url.is_not(None),
            )
        )

    def public_counts_by_category(self) -> dict[uuid.UUID, int]:
        """Products a visitor can see, per category of their shop -- the same
        rule as the catalogue, so a category's count is what opening it
        shows."""
        visible = self.public_query().with_only_columns(
            Business.category_id, func.count(BusinessItem.id)
        ).group_by(Business.category_id)
        return {row[0]: row[1] for row in self.db.execute(visible).all() if row[0] is not None}

    def top_rated(self, limit: int) -> list[BusinessItem]:
        """Products of the best-rated shops: a product is rated as its shop
        is (the owners' decision, 29 Oct 2026), so only rated shops count,
        the busier of two equal averages first, then the newest product."""
        stmt = self._with_relations(
            self.public_query()
            .where(Business.rating_count > 0)
            .order_by(
                Business.rating_average.desc(),
                Business.rating_count.desc(),
                BusinessItem.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def top_viewed(self, since: date, limit: int) -> list[BusinessItem]:
        """The products opened most often since ``since``. Views, never
        people: the counter stores nothing about who looked."""
        views = (
            select(
                ListingViewDaily.subject_id.label("item_id"),
                func.sum(ListingViewDaily.views).label("views"),
            )
            .where(
                ListingViewDaily.subject_type == ViewSubject.PRODUCT,
                ListingViewDaily.day >= since,
            )
            .group_by(ListingViewDaily.subject_id)
            .subquery()
        )
        stmt = self._with_relations(
            self.public_query()
            .join(views, views.c.item_id == BusinessItem.id)
            .order_by(views.c.views.desc(), BusinessItem.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def related(self, item: BusinessItem, limit: int) -> list[BusinessItem]:
        """What else a visitor looking at ``item`` might add to the order:
        the same shop's other products first, then products in the same
        category from other shops, the best-rated sellers first."""
        same_shop = BusinessItem.business_id == item.business_id
        stmt = self._with_relations(
            self.public_query()
            .where(
                BusinessItem.id != item.id,
                or_(same_shop, Business.category_id == item.business.category_id),
            )
            .order_by(
                case((same_shop, 0), else_=1),
                nullslast(Business.rating_average.desc()),
                BusinessItem.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def most_ordered(self, since: date, limit: int) -> list[BusinessItem]:
        """The products ordered most since ``since``, by units asked for.
        An order line keeps its product only while the product exists, and a
        product a visitor cannot see is left out like everywhere else."""
        ordered = (
            select(
                OrderLine.item_id.label("item_id"),
                func.sum(OrderLine.quantity).label("units"),
            )
            .join(Order, Order.id == OrderLine.order_id)
            .where(OrderLine.item_id.is_not(None), func.date(Order.created_at) >= since)
            .group_by(OrderLine.item_id)
            .subquery()
        )
        stmt = self._with_relations(
            self.public_query()
            .join(ordered, ordered.c.item_id == BusinessItem.id)
            .order_by(ordered.c.units.desc(), BusinessItem.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def public_counts_by_location(self) -> dict[uuid.UUID, int]:
        """Products a visitor can see, per place of their shop."""
        visible = self.public_query().with_only_columns(
            Business.location_id, func.count(BusinessItem.id)
        ).group_by(Business.location_id)
        return {row[0]: row[1] for row in self.db.execute(visible).all() if row[0] is not None}

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

    def public_slugs(self) -> list[tuple[str, object, str | None]]:
        """(slug, updated_at, photo) for the sitemap.

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
            select(public.c.slug, public.c.updated_at, public.c.image_url).order_by(
                public.c.updated_at.desc()
            )
        ).all()
        return [(row[0], row[1], row[2]) for row in rows]

    def _apply_filters(
        self,
        stmt: Select[tuple[BusinessItem]],
        *,
        q: str | None,
        category_slug: str | None,
        location_slug: str | None,
        origin: GoodsOrigin | None = None,
        displaced: bool = False,
    ) -> Select[tuple[BusinessItem]]:
        if displaced:
            # Only holders who chose to show it: the filter must not reveal
            # by omission what the badge would not show.
            stmt = stmt.where(
                Business.owner_id.in_(select(User.id).where(User.publishes_displacement()))
            )

        if origin is not None:
            # The product's own mark, not its shop's: a shop selling both has
            # each of its goods under the door that describes it.
            stmt = stmt.where(BusinessItem.goods_origin == origin)

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
        self, stmt: Select[tuple[BusinessItem]], sort: SortOption, near: Point | None = None
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
        # A product is as near as the business selling it; without a
        # position, nearest falls back to newest.
        if sort == "nearest" and near is not None:
            return stmt.order_by(
                nearest_first(Business.latitude, Business.longitude, near),
                BusinessItem.created_at.desc(),
            )
        # A product is rated as its business is; unrated sellers last.
        if sort == "rating":
            return stmt.order_by(
                nullslast(Business.rating_average.desc()),
                Business.rating_count.desc(),
                BusinessItem.created_at.desc(),
            )
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
        origin: GoodsOrigin | None = None,
        displaced: bool = False,
        sort: SortOption = "newest",
        near: Point | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> Page[BusinessItem]:
        """Paginated public search. Never returns an unreachable product."""
        filtered = self._apply_filters(
            self.public_query(),
            q=q,
            category_slug=category_slug,
            location_slug=location_slug,
            origin=origin,
            displaced=displaced,
        )

        total = int(
            self.db.execute(select(func.count()).select_from(filtered.subquery())).scalar_one()
        )

        stmt = self._apply_sort(self._with_relations(filtered), sort, near)
        rows = (
            self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
            .unique()
            .scalars()
            .all()
        )
        return Page(items=list(rows), total=total, page=page, page_size=page_size)


def make_repository(db: Session) -> ItemRepository:
    return ItemRepository(db)
