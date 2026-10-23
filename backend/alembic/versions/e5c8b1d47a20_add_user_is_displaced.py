"""ask an applicant whether they are currently displaced from the South

Revision ID: e5c8b1d47a20
Revises: d2b7a4c91e53
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e5c8b1d47a20"
down_revision = "d2b7a4c91e53"
branch_labels = None
depends_on = None


def _has_column() -> bool:
    columns = sa.inspect(op.get_bind()).get_columns("users")
    return any(column["name"] == "is_displaced" for column in columns)


def upgrade() -> None:
    # Nullable: every account that predates the question has not answered it.
    if not _has_column():
        op.add_column("users", sa.Column("is_displaced", sa.Boolean(), nullable=True))


def downgrade() -> None:
    if _has_column():
        op.drop_column("users", "is_displaced")
