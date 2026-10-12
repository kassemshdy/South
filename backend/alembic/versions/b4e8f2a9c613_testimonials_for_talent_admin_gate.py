"""testimonials for service profiles; the administrator's approval publishes

The owners changed two things at once:

- A testimonial is published by an administrator's approval alone. The
  owner no longer approves or hides; the administrator can still delete.
  Rows an administrator had passed to an owner (``PENDING_OWNER``) go back to
  ``PENDING_REVIEW``: under the old rule clearing one meant "not abuse", not
  "publish", so nothing is published here without a decision under the new
  rule. The enum value stays, unused, because Postgres cannot drop one.
- Service profiles take testimonials and stars too. A testimonial now
  belongs to exactly one of a business or a talent profile, and a profile
  carries its own average and count so the directory can sort on them.

Guarded like the migrations before it.

Revision ID: b4e8f2a9c613
Revises: a7c3e9f15b28
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b4e8f2a9c613"
down_revision = "a7c3e9f15b28"
branch_labels = None
depends_on = None

_CHECK = "ck_testimonials_one_subject"
_INDEX = "ix_testimonials_talent_profile_id"


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _has_check(table: str, name: str) -> bool:
    return any(
        c["name"] == name for c in sa.inspect(op.get_bind()).get_check_constraints(table)
    )


def _has_index(table: str, name: str) -> bool:
    return any(i["name"] == name for i in sa.inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_column("testimonials", "talent_profile_id"):
        op.add_column(
            "testimonials",
            sa.Column(
                "talent_profile_id",
                sa.Uuid(),
                sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    if not _has_index("testimonials", _INDEX):
        op.create_index(_INDEX, "testimonials", ["talent_profile_id", "status"])
    op.alter_column("testimonials", "business_id", nullable=True)
    if not _has_check("testimonials", _CHECK):
        op.create_check_constraint(
            _CHECK, "testimonials", "num_nonnulls(business_id, talent_profile_id) = 1"
        )

    if not _has_column("talent_profiles", "rating_average"):
        op.add_column(
            "talent_profiles", sa.Column("rating_average", sa.Numeric(3, 2), nullable=True)
        )
    if not _has_column("talent_profiles", "rating_count"):
        op.add_column(
            "talent_profiles",
            sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        )

    op.execute(
        "UPDATE testimonials SET status = 'PENDING_REVIEW' WHERE status = 'PENDING_OWNER'"
    )


def downgrade() -> None:
    if _has_column("talent_profiles", "rating_count"):
        op.drop_column("talent_profiles", "rating_count")
    if _has_column("talent_profiles", "rating_average"):
        op.drop_column("talent_profiles", "rating_average")
    if _has_check("testimonials", _CHECK):
        op.drop_constraint(_CHECK, "testimonials", type_="check")
    op.execute("DELETE FROM testimonials WHERE business_id IS NULL")
    op.alter_column("testimonials", "business_id", nullable=False)
    if _has_index("testimonials", _INDEX):
        op.drop_index(_INDEX, table_name="testimonials")
    if _has_column("testimonials", "talent_profile_id"):
        op.drop_column("testimonials", "talent_profile_id")
