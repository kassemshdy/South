"""an optional star rating on a testimonial, and each business's average

The owners asked for a five-star rating beside the written testimonial, and
for the directories to sort by it, rated listings first. The rating is
optional, 1 to 5; the business keeps the average and count of the ratings on
its *published* testimonials, so the directory can sort on a column rather
than aggregate per request. Nothing here changes an existing row's meaning:
every testimonial today has no rating, and every business a count of 0.

Guarded like the migrations before it.

Revision ID: c7f2a9e4b318
Revises: b6e1d3f9a204
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c7f2a9e4b318"
down_revision = "b6e1d3f9a204"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("testimonials", "rating"):
        op.add_column("testimonials", sa.Column("rating", sa.SmallInteger(), nullable=True))
        op.create_check_constraint(
            "ck_testimonials_rating_range", "testimonials", "rating BETWEEN 1 AND 5"
        )
    if not _has_column("businesses", "rating_average"):
        op.add_column("businesses", sa.Column("rating_average", sa.Numeric(3, 2), nullable=True))
    if not _has_column("businesses", "rating_count"):
        op.add_column(
            "businesses",
            sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("businesses", "rating_count"):
        op.drop_column("businesses", "rating_count")
    if _has_column("businesses", "rating_average"):
        op.drop_column("businesses", "rating_average")
    if _has_column("testimonials", "rating"):
        op.drop_constraint("ck_testimonials_rating_range", "testimonials", type_="check")
        op.drop_column("testimonials", "rating")
