"""A sign-up limit on an activity, and the administrator's override (the
owners' ticket, 16 Nov 2026).

Revision ID: b8d4f0a3c5e7
Revises: a7c3e9f2b4d6
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b8d4f0a3c5e7"
down_revision = "a7c3e9f2b4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("registration_limit", sa.Integer(), nullable=True))
    op.add_column(
        "activities", sa.Column("registration_override", sa.String(length=10), nullable=True)
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
