"""Staff switches on a shop's Shopify store (the owners' request, 21 Nov 2026).

``store_links.sync_paused`` stops product changes being sent to the store;
``store_links.hidden`` takes the store's buy buttons and link off the site
while it stays linked. Both default to off, so nothing changes for a store
already connected. Adds columns only.

Revision ID: f4b8d2a6c1e7
Revises: e3a7c9d1f5b2
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f4b8d2a6c1e7"
down_revision = "e3a7c9d1f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_links",
        sa.Column("sync_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "store_links",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    # Nothing is dropped here (the owners' rule of 4 Nov 2026): undoing this
    # is a new migration through app/database/migration_safety.py.
    pass
