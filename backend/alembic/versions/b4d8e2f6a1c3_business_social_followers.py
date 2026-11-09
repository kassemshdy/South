"""Businesses: Instagram and Facebook follower counts, fetched through Apify.

Revision ID: b4d8e2f6a1c3
Revises: e7a3c9d1f5b2
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b4d8e2f6a1c3"
down_revision = "e7a3c9d1f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("instagram_followers", sa.Integer(), nullable=True))
    op.add_column("businesses", sa.Column("facebook_followers", sa.Integer(), nullable=True))
    op.add_column(
        "businesses",
        sa.Column("followers_checked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
