"""Links to videos of a services provider's work (the owners' review,
12 Nov 2026).

Revision ID: e5b9c2d7a4f1
Revises: d3a8f1c6b5e2
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e5b9c2d7a4f1"
down_revision = "d3a8f1c6b5e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talent_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_talent_videos_profile_id", "talent_videos", ["profile_id"])


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
