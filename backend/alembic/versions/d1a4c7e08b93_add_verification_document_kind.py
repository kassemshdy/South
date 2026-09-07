"""add a kind discriminator to owner verification documents

A talent profile may attach a CV alongside the ID scan every owner uploads.
Both are personal documents stored the same admin-gated way, so they share a
table and are told apart by ``kind`` rather than by a second table. The old
one-row-per-user unique index becomes one row per user *per kind*.

Guarded the same way the earlier migrations are: a schema that already ran
ahead of its recorded version must still be able to reconcile to head
instead of crashing on DuplicateColumn.

Revision ID: d1a4c7e08b93
Revises: c5d9f31a08b2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d1a4c7e08b93"
down_revision = "c5d9f31a08b2"
branch_labels = None
depends_on = None

_TABLE = "owner_verification_documents"
_INDEX = "ix_owner_verification_documents_user_id"
_UNIQUE = "uq_owner_document_user_kind"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _index(table: str, name: str) -> dict | None:
    if not _has_table(table):
        return None
    return next((i for i in _inspector().get_indexes(table) if i["name"] == name), None)


def _has_constraint(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return name in {c["name"] for c in _inspector().get_unique_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(_TABLE):
        return

    sa.Enum("IDENTITY", "CV", name="verification_document_kind").create(
        bind, checkfirst=True
    )
    kind = postgresql.ENUM(
        "IDENTITY", "CV", name="verification_document_kind", create_type=False
    )

    if not _has_column(_TABLE, "kind"):
        # Every row that exists today is an ID scan, hence the server default.
        op.add_column(
            _TABLE,
            sa.Column("kind", kind, nullable=False, server_default="IDENTITY"),
        )

    # The lookup index made a user's document unique on its own, which would
    # now forbid a CV next to an ID. Postgres cannot drop uniqueness in place,
    # so it is recreated under the same name the model still expects.
    existing = _index(_TABLE, _INDEX)
    if existing is not None and existing.get("unique"):
        op.drop_index(_INDEX, table_name=_TABLE)
        existing = None
    if existing is None:
        op.create_index(_INDEX, _TABLE, ["user_id"])
    if not _has_constraint(_TABLE, _UNIQUE):
        op.create_unique_constraint(_UNIQUE, _TABLE, ["user_id", "kind"])


def downgrade() -> None:
    op.drop_constraint(_UNIQUE, _TABLE, type_="unique")
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, "kind")
    op.create_index(_INDEX, _TABLE, ["user_id"], unique=True)
    sa.Enum(name="verification_document_kind").drop(op.get_bind(), checkfirst=True)
