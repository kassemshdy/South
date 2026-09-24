"""let a talent profile list its social accounts, optionally

The CEO's answer on adding social links to talent profiles: optional. The
same shape as a shop's -- one row per platform, the existing social_platform
enum -- so the two are normalised and rendered the same way.

Revision ID: f6c1a8e93b25
Revises: e5b9c3d72a14
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f6c1a8e93b25"
down_revision = "e5b9c3d72a14"
branch_labels = None
depends_on = None

_PLATFORMS = ("INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "WHATSAPP", "WEBSITE")


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("talent_social_links"):
        return
    op.create_table(
        "talent_social_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "platform",
            postgresql.ENUM(*_PLATFORMS, name="social_platform", create_type=False),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.UniqueConstraint("profile_id", "platform", name="uq_talent_social_platform"),
    )
    op.create_index("ix_talent_social_links_profile_id", "talent_social_links", ["profile_id"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("talent_social_links"):
        op.drop_index("ix_talent_social_links_profile_id", "talent_social_links")
        op.drop_table("talent_social_links")
