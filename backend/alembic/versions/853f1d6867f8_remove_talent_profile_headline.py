"""remove talent profile headline

Revision ID: 853f1d6867f8
Revises: 0aa27d4f9f5a
Create Date: 2026-09-14 09:27:49.572561+00:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = '853f1d6867f8'
down_revision = '0aa27d4f9f5a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: autogenerate also proposed dropping the trigram GIN indexes on
    # business_items/businesses/talent_profiles search columns -- those are
    # raw-SQL indexes not tracked by SQLAlchemy metadata, so autogenerate
    # always misreads them as removed. Left untouched here deliberately.
    op.drop_column('talent_profiles', 'headline')


def downgrade() -> None:
    op.add_column(
        'talent_profiles',
        sa.Column('headline', sa.VARCHAR(length=300), autoincrement=False, nullable=True),
    )
