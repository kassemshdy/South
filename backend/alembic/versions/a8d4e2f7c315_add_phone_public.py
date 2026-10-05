"""let a listing's owner keep their phone numbers off the public page

The owners asked that everyone listing on the platform give a phone number
and choose whether the public sees it. Not null with a default of true:
every listing that exists today shows its numbers, so none is hidden by
this migration.

Guarded like the migrations before it.

Revision ID: a8d4e2f7c315
Revises: f3a9c2e6b471
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a8d4e2f7c315"
down_revision = "f3a9c2e6b471"
branch_labels = None
depends_on = None

_TABLES = ("businesses", "talent_profiles")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    for table in _TABLES:
        if not _has_column(table, "phone_public"):
            op.add_column(
                table,
                sa.Column("phone_public", sa.Boolean(), nullable=False, server_default=sa.true()),
            )


def downgrade() -> None:
    for table in _TABLES:
        if _has_column(table, "phone_public"):
            op.drop_column(table, "phone_public")
