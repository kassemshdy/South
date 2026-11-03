"""Questions and answers on a service provider's profile.

Revision ID: b8d4f6a2c1e3
Revises: a7c3e5f1b9d2
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b8d4f6a2c1e3"
down_revision = "a7c3e5f1b9d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talent_faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.String(200), nullable=False),
        sa.Column("answer", sa.String(1000), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_talent_faqs_profile_id", "talent_faqs", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_talent_faqs_profile_id", table_name="talent_faqs")
    op.drop_table("talent_faqs")
