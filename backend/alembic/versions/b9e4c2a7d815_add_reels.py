"""the home page's reels: links to Instagram posts an administrator chooses

Additive: a new table, created only if absent, like the migrations before it.

Revision ID: b9e4c2a7d815
Revises: f1c6a9d3b507
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b9e4c2a7d815"
down_revision = "f1c6a9d3b507"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("reels"):
        return
    op.create_table(
        "reels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("shortcode", sa.String(64), nullable=False),
        sa.Column("caption_ar", sa.Text(), nullable=True),
        sa.Column("caption_en", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("cover_storage_key", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("shortcode", name="uq_reels_shortcode"),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("reels"):
        op.drop_table("reels")
