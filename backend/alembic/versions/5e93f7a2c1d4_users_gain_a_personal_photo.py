"""users gain a personal photo

The account holder's own photo — a face, not a logo. It belongs with the
identity columns rather than on any listing: one account may own several
businesses and the person behind them does not change between listings.

Stored as a URL and a storage key, the same pair talent profiles use, because
the bytes go through ImageService and land in object storage like every other
image here. What makes it admin-only is not where it is stored but that no
public schema carries it, which is the same protection the identity columns
already have and what tests/test_identity.py pins.

Revision ID: 5e93f7a2c1d4
Revises: 4d82a1c9b3e7
Create Date: 2026-09-18 09:00:00.000000+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "5e93f7a2c1d4"
down_revision = "4d82a1c9b3e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("photo_url", sa.String(length=500), nullable=True))
    op.add_column(
        "users", sa.Column("photo_storage_key", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "photo_storage_key")
    op.drop_column("users", "photo_url")
