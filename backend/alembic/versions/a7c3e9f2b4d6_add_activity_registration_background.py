"""The background question on an activity's sign-up form (the owners'
ticket, 15 Nov 2026).

Revision ID: a7c3e9f2b4d6
Revises: e5b9c2d7a4f1
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a7c3e9f2b4d6"
down_revision = "e5b9c2d7a4f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activity_registrations",
        sa.Column("background", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
