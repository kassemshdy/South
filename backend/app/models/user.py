from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.business import Business


class User(Base, TimestampMixin):
    """A platform account.

    Owners authenticate by phone + OTP and have no password; administrators
    authenticate by email + password and have no phone. Both live in this table
    so authorization is a single role check.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Stored normalized as E.164, e.g. +9613123456.
    phone_number: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.OWNER,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Bumped to invalidate every JWT previously issued to this user.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    businesses: Mapped[list[Business]] = relationship(
        back_populates="owner",
        foreign_keys="Business.owner_id",
        cascade="all, delete-orphan",
    )

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
