"""Staff roles: an activities editor and a reels-and-stories editor.

Revision ID: c4e8a2f6b1d3
Revises: b3f7d9e1a5c2
"""

from __future__ import annotations

from alembic import op

revision = "c4e8a2f6b1d3"
down_revision = "b3f7d9e1a5c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres 12+ adds an enum value inside a transaction; nothing here uses
    # the new values in the same transaction, which is the one restriction.
    op.execute("ALTER TYPE staff_role ADD VALUE IF NOT EXISTS 'ACTIVITIES'")
    op.execute("ALTER TYPE staff_role ADD VALUE IF NOT EXISTS 'REELS'")


def downgrade() -> None:
    # Postgres cannot drop an enum value, and nothing is dropped here anyway
    # (AGENTS.md): an account with either role keeps it.
    pass
