"""Per-activity sign-up questions: ask the background question or not, and
ask for the main place of residence (ticket 6f0b9420, 22 Nov 2026).

Revision ID: a9d3f7b1c5e8
Revises: f4b8d2a6c1e7
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a9d3f7b1c5e8"
down_revision = "f4b8d2a6c1e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("ask_background", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "activities",
        sa.Column("ask_residence", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "activity_registrations",
        sa.Column("residence", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
