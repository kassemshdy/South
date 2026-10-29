"""site_settings.value: text instead of 500 characters

The growth page's offer and the WhatsApp login message are stored here and
are allowed up to 5,000 and 2,000 characters by their schemas, but the
column held 500, so saving a real offer failed with a 500 error.

Revision ID: d7a4e2b9c1f3
Revises: c5e2a9d4f716
Create Date: 2026-10-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d7a4e2b9c1f3"
down_revision = "c5e2a9d4f716"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "site_settings",
        "value",
        type_=sa.Text(),
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Anything longer than the old limit is cut rather than refusing to
    # downgrade.
    op.alter_column(
        "site_settings",
        "value",
        type_=sa.String(length=500),
        existing_type=sa.Text(),
        existing_nullable=False,
        postgresql_using="left(value, 500)",
    )
