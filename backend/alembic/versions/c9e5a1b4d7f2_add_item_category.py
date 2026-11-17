"""A product's own category (the owners' ticket, 16 Nov 2026).

Null means the product follows its shop's category, which is every
product saved before this.

Revision ID: c9e5a1b4d7f2
Revises: b8d4f0a3c5e7
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c9e5a1b4d7f2"
down_revision = "b8d4f0a3c5e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_items",
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_business_items_category_id", "business_items", ["category_id"])


def downgrade() -> None:
    # Dropping nothing: undoing this is a new migration (AGENTS.md).
    pass
