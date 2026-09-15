"""add intro video id to businesses and talent

One nullable column per listing table, holding a YouTube video id rather than
a URL — see ``app.core.urls.youtube_video_id`` for why.

Autogenerate also proposed dropping four pre-existing trigram (GIN) indexes,
which it cannot see because they are created with raw DDL rather than through
the model metadata. Those drops are removed here: this revision adds two
columns and nothing else.

Revision ID: 18c64fbbe097
Revises: 22bb94847e57
Create Date: 2026-09-15 08:22:40.847614+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "18c64fbbe097"
down_revision = "22bb94847e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses", sa.Column("youtube_video_id", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "talent_profiles", sa.Column("youtube_video_id", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("talent_profiles", "youtube_video_id")
    op.drop_column("businesses", "youtube_video_id")
