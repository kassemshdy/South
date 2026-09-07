from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, pg_enum, uuid_pk
from app.models.enums import VerificationDocumentKind

if TYPE_CHECKING:
    from app.models.user import User


class OwnerVerificationDocument(Base):
    """Metadata for an owner's personal document; the bytes live in storage.

    One row per user *per kind* — an ID scan and a CV are separate rows, and a
    re-upload replaces the previous row of that kind. Deliberately has no
    public ``url`` column — unlike :class:`~app.models.business.BusinessImage`,
    this must never be reachable except through the admin-gated download
    endpoint.
    """

    __tablename__ = "owner_verification_documents"
    __table_args__ = (UniqueConstraint("user_id", "kind", name="uq_owner_document_user_kind"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[VerificationDocumentKind] = mapped_column(
        pg_enum(VerificationDocumentKind, "verification_document_kind"),
        nullable=False,
        default=VerificationDocumentKind.IDENTITY,
        server_default=VerificationDocumentKind.IDENTITY.value,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="documents")
