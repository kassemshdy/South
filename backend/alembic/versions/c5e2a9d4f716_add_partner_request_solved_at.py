"""partner requests: a solved date, so a handled request is archived, not deleted

Additive: one nullable column, added only if absent, like the migrations
before it.

Revision ID: c5e2a9d4f716
Revises: a3c7e1f9b240
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c5e2a9d4f716"
down_revision = "a3c7e1f9b240"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("partner_requests")}
    if "solved_at" not in existing:
        op.add_column(
            "partner_requests",
            sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("partner_requests", "solved_at")
