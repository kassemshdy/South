"""A photo on each priced service (the owners' review, 12 Nov 2026).

Revision ID: d3a8f1c6b5e2
Revises: c7e1a9d3f2b4
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d3a8f1c6b5e2"
down_revision = "c7e1a9d3f2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "talent_service_offers", sa.Column("image_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "talent_service_offers",
        sa.Column("image_storage_key", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
