"""the about page's team section: six photographs, each with a caption

Additive: a new table, created only if absent, like the migrations before it.

Revision ID: d4a8c1e7f925
Revises: c7f2a9e4b318
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d4a8c1e7f925"
down_revision = "c7f2a9e4b318"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("team_members"):
        return
    op.create_table(
        "team_members",
        sa.Column("slot", sa.SmallInteger(), autoincrement=False, primary_key=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("photo_storage_key", sa.String(500), nullable=True),
        sa.Column("caption_ar", sa.Text(), nullable=True),
        sa.Column("caption_en", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("team_members"):
        op.drop_table("team_members")
