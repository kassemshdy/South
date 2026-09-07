from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk
from app.models.enums import UserRole, VerificationDocumentKind

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.talent import TalentProfile
    from app.models.verification import OwnerVerificationDocument


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
    # A second, owner-supplied contact number collected for identity
    # verification; distinct from the login phone above and never published.
    # Not unique: a shared family/business line could reasonably belong to
    # more than one account.
    personal_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    talent_profile: Mapped[TalentProfile | None] = relationship(
        back_populates="owner",
        foreign_keys="TalentProfile.owner_id",
        cascade="all, delete-orphan",
        uselist=False,
    )
    # One collection, not a relationship per kind: two writable relationships
    # over the same rows would need `overlaps=` and still confuse the unit of
    # work. The per-kind accessors below are what call sites actually use.
    documents: Mapped[list[OwnerVerificationDocument]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def document_of(
        self, kind: VerificationDocumentKind
    ) -> OwnerVerificationDocument | None:
        return next((d for d in self.documents if d.kind is kind), None)

    @property
    def verification_document(self) -> OwnerVerificationDocument | None:
        """The owner's ID scan, the document every account may upload."""
        return self.document_of(VerificationDocumentKind.IDENTITY)

    @property
    def cv_document(self) -> OwnerVerificationDocument | None:
        """The résumé a talent profile may attach. Admin-gated like the ID."""
        return self.document_of(VerificationDocumentKind.CV)

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
