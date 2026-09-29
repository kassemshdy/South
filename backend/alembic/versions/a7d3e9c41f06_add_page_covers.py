"""let an administrator set the cover photograph of each public page

Revision ID: a7d3e9c41f06
Revises: f6c1a8e93b25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a7d3e9c41f06"
down_revision = "f6c1a8e93b25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("page_covers"):
        return
    op.create_table(
        "page_covers",
        sa.Column("page_key", sa.String(40), primary_key=True),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("page_covers"):
        op.drop_table("page_covers")
