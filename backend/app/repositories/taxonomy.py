from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.enums import LocationType
from app.models.taxonomy import Category, Location
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def list_all(self, *, active_only: bool = True) -> list[Category]:
        stmt = select(Category).order_by(Category.sort_order, Category.name_ar)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def get_by_slug(self, slug: str) -> Category | None:
        return self.db.execute(
            select(Category).where(Category.slug == slug)
        ).scalar_one_or_none()

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Category.id).where(Category.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None


class LocationRepository(BaseRepository[Location]):
    model = Location

    def list_all(self, *, active_only: bool = True) -> list[Location]:
        stmt = select(Location).order_by(Location.sort_order, Location.name_ar)
        if active_only:
            stmt = stmt.where(Location.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def list_by_type(self, location_type: LocationType) -> list[Location]:
        return list(
            self.db.execute(
                select(Location)
                .where(Location.type == location_type, Location.is_active.is_(True))
                .order_by(Location.sort_order, Location.name_ar)
            )
            .scalars()
            .all()
        )

    def get_by_slug(self, slug: str) -> Location | None:
        return self.db.execute(
            select(Location).where(Location.slug == slug)
        ).scalar_one_or_none()

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Location.id).where(Location.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Location.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def has_children(self, location_id: uuid.UUID) -> bool:
        return (
            self.db.execute(
                select(Location.id).where(Location.parent_id == location_id).limit(1)
            ).scalar_one_or_none()
            is not None
        )
