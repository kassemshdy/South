from __future__ import annotations

import uuid

from sqlalchemy import ColumnElement, func, or_, select

from app.models.business import Business
from app.models.enums import UserRole
from app.models.talent import TalentProfile
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_phone(self, phone_number: str) -> User | None:
        return self.db.execute(
            select(User).where(User.phone_number == phone_number)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        ).scalar_one_or_none()

    def create_owner(self, phone_number: str, display_name: str | None = None) -> User:
        return self.add(
            User(phone_number=phone_number, display_name=display_name, role=UserRole.OWNER)
        )

    def list_users(
        self,
        *,
        limit: int,
        offset: int,
        query: str | None = None,
        role: UserRole | None = None,
        active: bool | None = None,
        sort: str = "newest",
    ) -> tuple[list[User], int]:
        """Accounts for the admin list, searched, filtered and sorted.

        ``query`` matches a phone number however it is typed (``03 123 456``,
        ``+961 3 123456``, ``3123456``), or a name: the display name, the
        account holder's own name, the email, or the name of a shop or
        service profile the account owns.
        """
        stmt = select(User)
        if query and query.strip():
            text = query.strip()
            pattern = f"%{text}%"
            owned_shop = select(Business.owner_id).where(Business.name.ilike(pattern))
            owned_profile = select(TalentProfile.owner_id).where(
                TalentProfile.display_name.ilike(pattern)
            )
            conditions: list[ColumnElement[bool]] = [
                User.display_name.ilike(pattern),
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.id.in_(owned_shop),
                User.id.in_(owned_profile),
            ]
            digits = "".join(ch for ch in text if ch.isdigit())
            if len(digits) >= 3:
                # Stored as +961..., typed with a leading 0 or the 961 prefix.
                local = digits.removeprefix("961").removeprefix("0") or digits
                for column in (User.phone_number, User.personal_phone_number):
                    conditions.append(column.contains(local))
            stmt = stmt.where(or_(*conditions))
        if role is not None:
            stmt = stmt.where(User.role == role)
        if active is not None:
            stmt = stmt.where(User.is_active.is_(active))

        total = int(
            self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        )
        if sort == "oldest":
            stmt = stmt.order_by(User.created_at.asc())
        elif sort == "name":
            stmt = stmt.order_by(
                func.coalesce(User.display_name, User.full_name, User.email).asc().nulls_last(),
                User.created_at.desc(),
            )
        elif sort == "listings":
            listings = (
                select(func.count())
                .select_from(Business)
                .where(Business.owner_id == User.id)
                .scalar_subquery()
            )
            stmt = stmt.order_by(listings.desc(), User.created_at.desc())
        else:
            stmt = stmt.order_by(User.created_at.desc())
        rows = self.db.execute(stmt.limit(limit).offset(offset)).scalars().all()
        return list(rows), total

    def count_by_role(self, role: UserRole) -> int:
        return int(
            self.db.execute(
                select(func.count()).select_from(User).where(User.role == role)
            ).scalar_one()
        )

    def list_by_role(self, role: UserRole) -> list[User]:
        """Every user with ``role`` — used for the feedback assignee picker,
        which only ever offers administrators."""
        return list(
            self.db.execute(
                select(User).where(User.role == role).order_by(User.display_name, User.email)
            )
            .scalars()
            .all()
        )

    def get_active(self, user_id: uuid.UUID) -> User | None:
        user = self.get(user_id)
        if user is None or not user.is_active:
            return None
        return user
