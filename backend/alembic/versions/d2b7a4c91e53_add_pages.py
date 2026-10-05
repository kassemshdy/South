"""let an administrator write the text of the site's static pages

Revision ID: d2b7a4c91e53
Revises: c4f1e8a3b927
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d2b7a4c91e53"
down_revision = "c4f1e8a3b927"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("pages"):
        return
    op.create_table(
        "pages",
        sa.Column("key", sa.String(40), primary_key=True),
        sa.Column("title_ar", sa.String(200), nullable=True),
        sa.Column("title_en", sa.String(200), nullable=True),
        sa.Column("summary_ar", sa.Text(), nullable=True),
        sa.Column("summary_en", sa.Text(), nullable=True),
        sa.Column("body_ar", sa.Text(), nullable=True),
        sa.Column("body_en", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("pages"):
        op.drop_table("pages")
