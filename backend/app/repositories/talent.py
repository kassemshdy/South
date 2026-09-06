"""Talent profile data access, including the public directory query.

Mirrors :mod:`app.repositories.business`: :meth:`TalentRepository.public_query`
is the single place that decides what an anonymous visitor may see, so the
"APPROVED only" rule has exactly one enforcement point for talent too.
"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.arabic import normalize_arabic
from app.core.pagination import Page
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from app.repositories.base import BaseRepository

SortOption = Literal["newest", "name", "oldest"]


class TalentSkillRepository(BaseRepository[TalentSkill]):
    model = TalentSkill

    def list_all(self, *, active_only: bool = True) -> list[TalentSkill]:
        stmt = select(TalentSkill).order_by(TalentSkill.sort_order, TalentSkill.name_ar)
        if active_only:
            stmt = stmt.where(TalentSkill.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def get_by_slug(self, slug: str) -> TalentSkill | None:
        return self.db.execute(
            select(TalentSkill).where(TalentSkill.slug == slug)
        ).scalar_one_or_none()

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(TalentSkill.id).where(TalentSkill.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(TalentSkill.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None


class TalentRepository(BaseRepository[TalentProfile]):
    model = TalentProfile

    # --- Loading -----------------------------------------------------------

    def _with_relations(
        self, stmt: Select[tuple[TalentProfile]]
    ) -> Select[tuple[TalentProfile]]:
        return stmt.options(
            joinedload(TalentProfile.skill),
            joinedload(TalentProfile.location).joinedload(Location.parent),
            selectinload(TalentProfile.images),
        )

    def get_with_relations(self, profile_id: uuid.UUID) -> TalentProfile | None:
        return self.db.execute(
            self._with_relations(select(TalentProfile).where(TalentProfile.id == profile_id))
        ).unique().scalar_one_or_none()

    def get_by_slug(self, slug: str, *, public_only: bool = True) -> TalentProfile | None:
        stmt = self._with_relations(select(TalentProfile).where(TalentProfile.slug == slug))
        if public_only:
            stmt = stmt.where(TalentProfile.status == BusinessStatus.APPROVED)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_for_owner(self, owner_id: uuid.UUID) -> TalentProfile | None:
        """The caller's own profile, in any status. At most one exists."""
        stmt = self._with_relations(
            select(TalentProfile).where(TalentProfile.owner_id == owner_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(TalentProfile.id).where(TalentProfile.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(TalentProfile.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    # --- Querying ----------------------------------------------------------

    def public_query(self) -> Select[tuple[TalentProfile]]:
        """Base statement for everything a visitor is allowed to see."""
        return select(TalentProfile).where(TalentProfile.status == BusinessStatus.APPROVED)

    def _apply_filters(
        self,
        stmt: Select[tuple[TalentProfile]],
        *,
        q: str | None,
        skill_slug: str | None,
        location_slug: str | None,
    ) -> Select[tuple[TalentProfile]]:
        if skill_slug:
            stmt = stmt.join(TalentSkill, TalentProfile.skill_id == TalentSkill.id).where(
                TalentSkill.slug == skill_slug
            )

        if location_slug:
            # Matching a district also matches the towns beneath it, exactly as
            # the business directory behaves.
            parent = select(Location.id).where(Location.slug == location_slug).scalar_subquery()
            stmt = stmt.where(
                or_(
                    TalentProfile.location_id.in_(
                        select(Location.id).where(Location.slug == location_slug)
                    ),
                    TalentProfile.location_id.in_(
                        select(Location.id).where(Location.parent_id.in_(parent))
                    ),
                )
            )

        if q:
            stmt = stmt.where(TalentProfile.search_text.like(f"%{normalize_arabic(q)}%"))

        return stmt

    def _apply_sort(
        self, stmt: Select[tuple[TalentProfile]], sort: SortOption
    ) -> Select[tuple[TalentProfile]]:
        if sort == "name":
            return stmt.order_by(TalentProfile.display_name.asc())
        if sort == "oldest":
            return stmt.order_by(TalentProfile.created_at.asc())
        return stmt.order_by(TalentProfile.created_at.desc())

    def search_public(
        self,
        *,
        q: str | None = None,
        skill_slug: str | None = None,
        location_slug: str | None = None,
        sort: SortOption = "newest",
        page: int = 1,
        page_size: int = 12,
    ) -> Page[TalentProfile]:
        """Paginated public search. Never returns a non-APPROVED profile."""
        filtered = self._apply_filters(
            self.public_query(), q=q, skill_slug=skill_slug, location_slug=location_slug
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

    def list_for_admin(
        self,
        *,
        status: BusinessStatus | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[TalentProfile]:
        stmt = select(TalentProfile)
        if status is not None:
            stmt = stmt.where(TalentProfile.status == status)
        if q:
            stmt = stmt.where(TalentProfile.search_text.like(f"%{normalize_arabic(q)}%"))

        total = int(
            self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        )

        # Oldest pending first: the review queue should be FIFO.
        order = (
            TalentProfile.submitted_at.asc()
            if status is BusinessStatus.PENDING_REVIEW
            else TalentProfile.created_at.desc()
        )
        rows = (
            self.db.execute(
                self._with_relations(stmt)
                .options(joinedload(TalentProfile.owner).joinedload(User.verification_document))
                .order_by(order)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return Page(items=list(rows), total=total, page=page, page_size=page_size)

    def get_for_admin(self, profile_id: uuid.UUID) -> TalentProfile | None:
        stmt = self._with_relations(
            select(TalentProfile).where(TalentProfile.id == profile_id)
        ).options(
            joinedload(TalentProfile.owner).joinedload(User.verification_document),
            selectinload(TalentProfile.moderation_actions),
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    # --- Aggregates --------------------------------------------------------

    def count_by_status(self) -> dict[BusinessStatus, int]:
        rows = self.db.execute(
            select(TalentProfile.status, func.count()).group_by(TalentProfile.status)
        ).all()
        return {row[0]: row[1] for row in rows}

    def approved_slugs(self) -> list[tuple[str, object]]:
        """(slug, updated_at) pairs for the sitemap — APPROVED only."""
        rows = self.db.execute(
            select(TalentProfile.slug, TalentProfile.updated_at)
            .where(TalentProfile.status == BusinessStatus.APPROVED)
            .order_by(TalentProfile.updated_at.desc())
        ).all()
        return [(row[0], row[1]) for row in rows]

    def recently_approved(self, limit: int = 8) -> list[TalentProfile]:
        stmt = self._with_relations(
            self.public_query().order_by(
                func.coalesce(TalentProfile.approved_at, TalentProfile.created_at).desc()
            )
        )
        return list(self.db.execute(stmt.limit(limit)).unique().scalars().all())

    def public_counts_by_skill(self) -> dict[uuid.UUID, int]:
        rows = self.db.execute(
            select(TalentProfile.skill_id, func.count())
            .where(TalentProfile.status == BusinessStatus.APPROVED)
            .group_by(TalentProfile.skill_id)
        ).all()
        return {row[0]: row[1] for row in rows if row[0] is not None}

    def public_profile_count(self) -> int:
        return int(
            self.db.execute(
                select(func.count()).select_from(self.public_query().subquery())
            ).scalar_one()
        )


def make_repository(db: Session) -> TalentRepository:
    return TalentRepository(db)
