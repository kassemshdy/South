"""talent profiles: a cover image, as businesses have

The owners' ticket of 29 Oct 2026: a service profile gets a wide cover image
across the top of its page, required before review like the photo. Two
nullable columns, added only if absent, like the migrations before it.

Revision ID: e8c4a1f6b392
Revises: d7b3e5f1a284
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e8c4a1f6b392"
down_revision = "d7b3e5f1a284"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("talent_profiles")}
    if "cover_url" not in existing:
        op.add_column("talent_profiles", sa.Column("cover_url", sa.String(500), nullable=True))
    if "cover_storage_key" not in existing:
        op.add_column(
            "talent_profiles", sa.Column("cover_storage_key", sa.String(500), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("talent_profiles", "cover_storage_key")
    op.drop_column("talent_profiles", "cover_url")
