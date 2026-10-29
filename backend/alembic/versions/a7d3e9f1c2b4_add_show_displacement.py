"""users.show_displacement: the holder's opt-in to show where they were displaced from

Revision ID: a7d3e9f1c2b4
Revises: f4c9d2e6b8a1
Create Date: 2026-10-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7d3e9f1c2b4"
down_revision = "f4c9d2e6b8a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Off for every existing account: they answered under a promise that
    # none of their identity would be shown.
    op.add_column(
        "users",
        sa.Column("show_displacement", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "show_displacement")
