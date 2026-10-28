"""articles: an optional category and place, for the listings shown under one

Additive: two nullable columns, added only if absent, like the migrations
before it. Deleting the category or place clears the link, not the article.

Revision ID: a3c7e1f9b240
Revises: d6a2f8c4e913
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a3c7e1f9b240"
down_revision = "d6a2f8c4e913"
branch_labels = None
depends_on = None

COLUMNS = (("category_id", "categories"), ("location_id", "locations"))


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("articles")}
    for column, table in COLUMNS:
        if column in existing:
            continue
        op.add_column("articles", sa.Column(column, postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_articles_{column}_{table}",
            "articles",
            table,
            [column],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for column, table in COLUMNS:
        op.drop_constraint(f"fk_articles_{column}_{table}", "articles", type_="foreignkey")
        op.drop_column("articles", column)
