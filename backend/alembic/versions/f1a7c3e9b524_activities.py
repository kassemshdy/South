"""activities: the home page's announcement carousel

The owners' ticket of 29 Oct 2026: development activities announced as a
carousel of photographs on the home page, each with a page of its own. A
new table, created only if absent, like the migrations before it.

Revision ID: f1a7c3e9b524
Revises: e8c4a1f6b392
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f1a7c3e9b524"
down_revision = "e8c4a1f6b392"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "activities" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "activities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.String(300), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("image_storage_key", sa.String(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_activities_slug", "activities", ["slug"], unique=True)
    op.create_index("ix_activities_archived_order", "activities", ["is_archived", "sort_order"])


def downgrade() -> None:
    op.drop_index("ix_activities_archived_order", table_name="activities")
    op.drop_index("ix_activities_slug", table_name="activities")
    op.drop_table("activities")
