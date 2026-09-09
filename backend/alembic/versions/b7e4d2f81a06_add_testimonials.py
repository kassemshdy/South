"""Add testimonials

Owner-approved praise on a business listing (#48). Submission is anonymous,
so there is no author foreign key -- ``author_name`` is whatever the visitor
typed and must not be mistaken for an account.

Revision ID: b7e4d2f81a06
Revises: f8c2b5a71d94
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7e4d2f81a06"
down_revision = "f8c2b5a71d94"
branch_labels = None
depends_on = None

STATUSES = ("PENDING", "APPROVED", "HIDDEN")

# `create_type=False` is honoured by the postgresql dialect's ENUM and
# silently ignored by the generic sa.Enum, which then emits a second
# CREATE TYPE from create_table and fails on DuplicateObject.
_status_column = postgresql.ENUM(*STATUSES, name="testimonial_status", create_type=False)
_status_type = postgresql.ENUM(*STATUSES, name="testimonial_status")


def upgrade() -> None:
    _status_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "testimonials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(length=80), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", _status_column, nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_testimonials_business_id_businesses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_testimonials"),
    )
    op.create_index("ix_testimonials_business_id", "testimonials", ["business_id"])
    op.create_index(
        "ix_testimonials_business_status", "testimonials", ["business_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_testimonials_business_status", table_name="testimonials")
    op.drop_index("ix_testimonials_business_id", table_name="testimonials")
    op.drop_table("testimonials")
    _status_type.drop(op.get_bind(), checkfirst=True)
