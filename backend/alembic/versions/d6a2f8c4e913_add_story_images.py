"""photo stories: an owner's photograph for their listing, shown for a day once approved

Additive: a new table, created only if absent, like the migrations before it.

Revision ID: d6a2f8c4e913
Revises: b9e4c2a7d815
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d6a2f8c4e913"
down_revision = "b9e4c2a7d815"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("story_images"):
        return
    op.create_table(
        "story_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "talent_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("image_storage_key", sa.String(500), nullable=False),
        sa.Column("caption", sa.String(200), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(business_id IS NULL) <> (talent_profile_id IS NULL)",
            name="ck_story_images_one_listing",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')",
            name="ck_story_images_known_status",
        ),
    )
    for column in ("owner_id", "business_id", "talent_profile_id", "expires_at"):
        op.create_index(f"ix_story_images_{column}", "story_images", [column])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("story_images"):
        op.drop_table("story_images")
