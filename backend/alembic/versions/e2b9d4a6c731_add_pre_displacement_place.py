"""where a displaced account holder lived before displacement

The owners asked that a seller who says they are displaced also say where
they lived before; where they live now is the place of residence already
asked. Nullable: nobody who answered before this has one, and only a
displaced applicant is asked. Identity, like the columns beside it -- never
published (tests/test_identity.py derives its list from the schema).

Guarded like the migrations before it.

Revision ID: e2b9d4a6c731
Revises: d4a8c1e7f925
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e2b9d4a6c731"
down_revision = "d4a8c1e7f925"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("users", "pre_displacement_place"):
        op.add_column(
            "users", sa.Column("pre_displacement_place", sa.String(200), nullable=True)
        )


def downgrade() -> None:
    if _has_column("users", "pre_displacement_place"):
        op.drop_column("users", "pre_displacement_place")
