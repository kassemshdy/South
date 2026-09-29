"""let an administrator set the site's contact details and social accounts

Revision ID: c4f1e8a3b927
Revises: a7d3e9c41f06
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c4f1e8a3b927"
down_revision = "a7d3e9c41f06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("site_settings"):
        return
    op.create_table(
        "site_settings",
        sa.Column("key", sa.String(40), primary_key=True),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("site_settings"):
        op.drop_table("site_settings")
