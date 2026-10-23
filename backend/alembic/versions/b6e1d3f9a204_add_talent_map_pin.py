"""a talent profile's place on the map, as a business already has

The owners asked for every seller to mark where they are on a map, shown on
the listing page and used to sort the directories nearest-first. Businesses
have had latitude and longitude since the initial schema; profiles get the
same pair, the same type. Nullable, because profiles that exist today have
none: the readiness check asks for one before a profile is submitted.

Guarded like the migrations before it.

Revision ID: b6e1d3f9a204
Revises: a8d4e2f7c315
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b6e1d3f9a204"
down_revision = "a8d4e2f7c315"
branch_labels = None
depends_on = None

_TABLES = ("talent_profiles",)
_COLUMNS = ("latitude", "longitude")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            if not _has_column(table, column):
                op.add_column(table, sa.Column(column, sa.Numeric(9, 6), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            if _has_column(table, column):
                op.drop_column(table, column)
