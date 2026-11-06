"""Businesses: addresses a listing had before it was renamed.

Revision ID: e7a3c9d1f5b2
Revises: d5f9b3a7c2e4
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e7a3c9d1f5b2"
down_revision = "d5f9b3a7c2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_slug_aliases",
        sa.Column("slug", sa.String(200), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_business_slug_aliases_business_id", "business_slug_aliases", ["business_id"]
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
