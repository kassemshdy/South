"""Declarative base and column conventions shared by every model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming convention so Alembic autogenerate produces stable,
# human-readable constraint names instead of database-assigned ones.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def pg_enum(python_enum: type, name: str) -> SAEnum:
    """A Postgres enum column that stores the member *values*, not their names.

    SQLAlchemy defaults to persisting ``BusinessStatus.APPROVED`` as the member
    name; every enum in this project is a ``str`` enum whose value is already
    the wire format, so ``values_callable`` keeps the database, the JSON API and
    the Python enum spelling one and the same thing.
    """
    return SAEnum(
        python_enum, name=name, values_callable=lambda e: [m.value for m in e]
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    """UUID primary key — user- and business-facing ids are never sequential."""
    return mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at / updated_at, stored as UTC-aware timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
