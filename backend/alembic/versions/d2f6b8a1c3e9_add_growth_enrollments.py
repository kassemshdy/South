"""The growth programme: shops staff take through it, step by step (the
owners' decision, 18 Nov 2026).

Revision ID: d2f6b8a1c3e9
Revises: c9e5a1b4d7f2
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d2f6b8a1c3e9"
down_revision = "c9e5a1b4d7f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stage", sa.String(length=20), nullable=False, server_default="CONTACTED"),
        sa.Column(
            "stage_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "enrolled_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("baseline_instagram", sa.Integer(), nullable=True),
        sa.Column("baseline_facebook", sa.Integer(), nullable=True),
        sa.Column("baseline_views_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baseline_clicks_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
