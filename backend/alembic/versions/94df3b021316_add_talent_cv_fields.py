"""add talent cv fields

Revision ID: 94df3b021316
Revises: d2f6a3c81b47
Create Date: 2026-09-14 05:40:46.170709+00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '94df3b021316'
down_revision = 'd2f6a3c81b47'
branch_labels = None
depends_on = None

# `create_type=False` is honoured by the postgresql dialect's ENUM and
# ignored by the generic sa.Enum -- which silently emits a second CREATE TYPE
# from add_column and fails the migration on DuplicateObject. The type is
# created and dropped explicitly below so the downgrade is complete.
_employment_type = postgresql.ENUM("FULL_TIME", "PART_TIME", name="employment_type")
_employment_column = postgresql.ENUM(
    "FULL_TIME", "PART_TIME", name="employment_type", create_type=False
)


def upgrade() -> None:
    # Note: autogenerate also proposed dropping the trigram GIN indexes on
    # business_items/businesses/talent_profiles search columns -- those are
    # raw-SQL indexes not tracked by SQLAlchemy metadata, so autogenerate
    # always misreads them as removed. Left untouched here deliberately.
    _employment_type.create(op.get_bind(), checkfirst=True)
    op.add_column('talent_profiles', sa.Column('education_years', sa.Integer(), nullable=True))
    op.add_column('talent_profiles', sa.Column('graduation_date', sa.Date(), nullable=True))
    op.add_column('talent_profiles', sa.Column('study_focus', sa.Text(), nullable=True))
    op.add_column('talent_profiles', sa.Column('professional_training', sa.Text(), nullable=True))
    op.add_column('talent_profiles', sa.Column('hobbies', sa.Text(), nullable=True))
    op.add_column(
        'talent_profiles', sa.Column('employment_type', _employment_column, nullable=True)
    )
    # A server default is required here (unlike the nullable columns above):
    # existing rows need a value the moment the NOT NULL constraint applies.
    op.add_column(
        'talent_profiles',
        sa.Column('remote_capable', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.alter_column('talent_profiles', 'remote_capable', server_default=None)


def downgrade() -> None:
    op.drop_column('talent_profiles', 'remote_capable')
    op.drop_column('talent_profiles', 'employment_type')
    op.drop_column('talent_profiles', 'hobbies')
    op.drop_column('talent_profiles', 'professional_training')
    op.drop_column('talent_profiles', 'study_focus')
    op.drop_column('talent_profiles', 'graduation_date')
    op.drop_column('talent_profiles', 'education_years')
    _employment_type.drop(op.get_bind(), checkfirst=True)
