"""job openings: a thumbnail chosen by staff

The admin's ticket (29 Oct 2026): a picture on each opening, on the list and
the page, set the way a workshop's cover is. Additive: two nullable columns,
added only if absent, like the migrations before it.

Revision ID: d7b3e5f1a284
Revises: c5e1f8a2d3b7
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d7b3e5f1a284"
down_revision = "c5e1f8a2d3b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("job_openings")}
    if "cover_url" not in existing:
        op.add_column("job_openings", sa.Column("cover_url", sa.String(), nullable=True))
    if "cover_storage_key" not in existing:
        op.add_column("job_openings", sa.Column("cover_storage_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("job_openings", "cover_storage_key")
    op.drop_column("job_openings", "cover_url")
