"""collab reels for the home page

A table of Instagram reels an administrator adds, each with a cover photo,
for the home page's reels row. New and empty: nothing existing changes.

Revision ID: a7d2c4e9f013
Revises: f1c6a9d3b507
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a7d2c4e9f013"
down_revision = "f1c6a9d3b507"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(160), nullable=True),
        sa.Column("instagram_kind", sa.String(8), nullable=False),
        sa.Column("instagram_code", sa.String(40), nullable=False),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("cover_storage_key", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("reels")
