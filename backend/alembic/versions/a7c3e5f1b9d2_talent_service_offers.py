"""Services with prices: one row per service a provider offers.

Revision ID: a7c3e5f1b9d2
Revises: f4a8c2d6e1b3
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7c3e5f1b9d2"
down_revision = "f4a8c2d6e1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talent_service_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("price_from", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_to", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "currency",
            postgresql.ENUM(name="currency", create_type=False),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("price_unit", sa.String(40), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_talent_service_offers_profile_id", "talent_service_offers", ["profile_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_talent_service_offers_profile_id", table_name="talent_service_offers")
    op.drop_table("talent_service_offers")
