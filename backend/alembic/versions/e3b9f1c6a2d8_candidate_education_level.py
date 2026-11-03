"""Candidate education level

The highest level a job seeker reached, as one of three answers, so the
directory can filter on it. The education rows stay free text; this is the
one value an employer filters by.

Revision ID: e3b9f1c6a2d8
Revises: d7a2c9e4b1f6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e3b9f1c6a2d8"
down_revision = "d7a2c9e4b1f6"
branch_labels = None
depends_on = None

LEVELS = ("SECONDARY_VOCATIONAL", "UNIVERSITY", "POSTGRADUATE")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*LEVELS, name="education_level").create(bind, checkfirst=True)
    op.add_column(
        "talent_profiles",
        sa.Column(
            "education_level",
            postgresql.ENUM(*LEVELS, name="education_level", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("talent_profiles", "education_level")
    postgresql.ENUM(*LEVELS, name="education_level").drop(op.get_bind(), checkfirst=True)
