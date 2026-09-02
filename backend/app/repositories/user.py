from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.enums import UserRole
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

    def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        total = int(self.db.execute(select(func.count()).select_from(User)).scalar_one())
        rows = (
            self.db.execute(
                select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def count_by_role(self, role: UserRole) -> int:
        return int(
            self.db.execute(
                select(func.count()).select_from(User).where(User.role == role)
            ).scalar_one()
        )

    def get_active(self, user_id: uuid.UUID) -> User | None:
        user = self.get(user_id)
        if user is None or not user.is_active:
            return None
        return user
