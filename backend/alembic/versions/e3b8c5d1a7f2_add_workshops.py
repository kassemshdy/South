"""workshops and their sign-ups

Revision ID: e3b8c5d1a7f2
Revises: d7a4e2b9c1f3
Create Date: 2026-10-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e3b8c5d1a7f2"
down_revision = "d7a4e2b9c1f3"
branch_labels = None
depends_on = None

_mode = postgresql.ENUM("ONLINE", "IN_PERSON", name="workshop_mode")
_currency = postgresql.ENUM(name="currency", create_type=False)


def upgrade() -> None:
    _mode.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workshops",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("trainer_name", sa.String(120), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "mode",
            postgresql.ENUM(name="workshop_mode", create_type=False),
            nullable=False,
            server_default="IN_PERSON",
        ),
        sa.Column("venue", sa.String(200), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", _currency, nullable=False, server_default="USD"),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("cover_storage_key", sa.String(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "category_id",
            sa.UUID(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            sa.UUID(),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_workshops_slug", "workshops", ["slug"], unique=True)
    op.create_index("ix_workshops_published_starts", "workshops", ["is_published", "starts_at"])
    op.create_table(
        "workshop_registrations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "workshop_id",
            sa.UUID(),
            sa.ForeignKey("workshops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(80), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_workshop_registrations_workshop_id", "workshop_registrations", ["workshop_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_workshop_registrations_workshop_id", table_name="workshop_registrations")
    op.drop_table("workshop_registrations")
    op.drop_index("ix_workshops_published_starts", table_name="workshops")
    op.drop_index("ix_workshops_slug", table_name="workshops")
    op.drop_table("workshops")
    _mode.drop(op.get_bind(), checkfirst=True)
