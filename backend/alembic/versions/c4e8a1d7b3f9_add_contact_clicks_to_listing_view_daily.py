"""Add contact_clicks to listing_view_daily

Counts presses of the WhatsApp and call buttons on a shop's page, per shop
per day, beside the views (staff ticket "analytics"). Still an integer and
nothing about the visitor.

Revision ID: c4e8a1d7b3f9
Revises: b9d2e6f4a1c8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4e8a1d7b3f9"
down_revision = "b9d2e6f4a1c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listing_view_daily",
        sa.Column("contact_clicks", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("listing_view_daily", "contact_clicks")
