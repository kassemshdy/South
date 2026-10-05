"""split talent profiles into services and job applications

The owners divided «services and skills» into two directories: people who
offer a service, and people looking for a job. Each profile's owner chooses.

Not null with a server default of ``SERVICE``: every profile that exists was
listed in the one directory there was, which offered services, so no row is
left without an answer. Indexed, because both directories filter on it.

Guarded like the migrations before it.

Revision ID: f3a9c2e6b471
Revises: e5c8b1d47a20
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f3a9c2e6b471"
down_revision = "e5c8b1d47a20"
branch_labels = None
depends_on = None

_KINDS = ("SERVICE", "JOB_SEEKER")
_INDEX = "ix_talent_profiles_kind"


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    return any(i["name"] == name for i in sa.inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    sa.Enum(*_KINDS, name="talent_kind").create(op.get_bind(), checkfirst=True)
    if not _has_column("talent_profiles", "kind"):
        op.add_column(
            "talent_profiles",
            sa.Column(
                "kind",
                postgresql.ENUM(*_KINDS, name="talent_kind", create_type=False),
                nullable=False,
                server_default="SERVICE",
            ),
        )
    if not _has_index("talent_profiles", _INDEX):
        op.create_index(_INDEX, "talent_profiles", ["kind"])


def downgrade() -> None:
    if _has_index("talent_profiles", _INDEX):
        op.drop_index(_INDEX, table_name="talent_profiles")
    if _has_column("talent_profiles", "kind"):
        op.drop_column("talent_profiles", "kind")
    sa.Enum(*_KINDS, name="talent_kind").drop(op.get_bind(), checkfirst=True)
