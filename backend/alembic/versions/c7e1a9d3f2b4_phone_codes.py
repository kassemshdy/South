"""Phone codes: one-time SMS codes for sign-up and password reset.

Revision ID: c7e1a9d3f2b4
Revises: b4d8e2f6a1c3
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c7e1a9d3f2b4"
down_revision = "b4d8e2f6a1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_phone_codes_phone_created", "phone_codes", ["phone", "created_at"])


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
