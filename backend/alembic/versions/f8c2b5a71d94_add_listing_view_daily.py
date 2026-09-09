"""Add listing_view_daily

A per-listing, per-day view counter, so an owner can see whether the
directory is doing anything for them (#46). Holds an integer and nothing
about the visitor -- no address, no cookie, no identifier.

The unique constraint is required rather than decorative: the counter is
written as an upsert that conflicts on it.

Revision ID: f8c2b5a71d94
Revises: a3f19c40b7e2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f8c2b5a71d94"
down_revision = "a3f19c40b7e2"
branch_labels = None
depends_on = None

SUBJECTS = ("BUSINESS", "TALENT", "PRODUCT")

# `create_type=False` is honoured by the postgresql dialect's ENUM and
# ignored by the generic sa.Enum -- which silently emits a second CREATE
# TYPE from create_table and fails the migration on DuplicateObject. The
# type is created and dropped explicitly below so the downgrade is complete.
_subject_column = postgresql.ENUM(*SUBJECTS, name="view_subject", create_type=False)
_subject_type = postgresql.ENUM(*SUBJECTS, name="view_subject")


def upgrade() -> None:
    _subject_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "listing_view_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_type", _subject_column, nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_listing_view_daily"),
        sa.UniqueConstraint(
            "subject_type", "subject_id", "day", name="uq_listing_view_daily_subject_day"
        ),
    )
    op.create_index(
        "ix_listing_view_daily_lookup",
        "listing_view_daily",
        ["subject_type", "subject_id", "day"],
    )


def downgrade() -> None:
    op.drop_index("ix_listing_view_daily_lookup", table_name="listing_view_daily")
    op.drop_table("listing_view_daily")
    _subject_type.drop(op.get_bind(), checkfirst=True)
