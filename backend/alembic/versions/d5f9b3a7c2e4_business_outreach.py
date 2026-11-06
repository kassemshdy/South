"""Businesses: staff follow-up of shops with nothing on sale (contacted, by whom, note).

Revision ID: d5f9b3a7c2e4
Revises: c4e8a2f6b1d3
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d5f9b3a7c2e4"
down_revision = "c4e8a2f6b1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses", sa.Column("outreach_contacted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "businesses",
        sa.Column(
            "outreach_contacted_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("businesses", sa.Column("outreach_note", sa.Text(), nullable=True))


def downgrade() -> None:
    # Nothing is dropped (AGENTS.md); undoing this is a new migration
    # through migration_safety.
    pass
