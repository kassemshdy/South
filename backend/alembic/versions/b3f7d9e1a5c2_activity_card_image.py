"""Activities: a 16:9 card image for list cards and link previews.

Revision ID: b3f7d9e1a5c2
Revises: a2e4c6b8d0f1
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b3f7d9e1a5c2"
down_revision = "a2e4c6b8d0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("card_image_url", sa.String(), nullable=True))
    op.add_column("activities", sa.Column("card_image_storage_key", sa.String(), nullable=True))


def downgrade() -> None:
    # Nothing is dropped (AGENTS.md: never drop a table or column that has
    # data); undoing this is a new migration through migration_safety.
    pass
