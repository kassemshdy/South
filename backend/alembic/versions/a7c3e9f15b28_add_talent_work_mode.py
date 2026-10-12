"""how a service is delivered: remotely, in person, or both

The owners asked that everyone offering a service say whether they work
remotely, in person or both, and that visitors can filter on it. Nullable:
no profile from before this has an answer, and a job application is not
asked. The old ``remote_capable`` flag is kept and derived from this, so
nothing that reads it changes; it is not used to backfill, because "can work
remotely" does not say whether they also work in person.

Guarded like the migrations before it.

Revision ID: a7c3e9f15b28
Revises: e2b9d4a6c731
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a7c3e9f15b28"
down_revision = "e2b9d4a6c731"
branch_labels = None
depends_on = None

_MODES = ("REMOTE", "ON_SITE", "BOTH")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    sa.Enum(*_MODES, name="work_mode").create(op.get_bind(), checkfirst=True)
    if not _has_column("talent_profiles", "work_mode"):
        op.add_column(
            "talent_profiles",
            sa.Column(
                "work_mode",
                postgresql.ENUM(*_MODES, name="work_mode", create_type=False),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("talent_profiles", "work_mode"):
        op.drop_column("talent_profiles", "work_mode")
    sa.Enum(*_MODES, name="work_mode").drop(op.get_bind(), checkfirst=True)
