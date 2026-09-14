"""add the seller's relation to the establishment, and years in the trade

The board ticket asking for a one-time seller profile lists twelve fields.
Ten of them already exist: the legal name and place of civil registration are
on ``users`` (one copy per account, shared by every listing it owns), and the
establishment name, activity, branch area, founding date, phone, email, links
and buyer contact channel are all on ``businesses`` already. Only two are new,
and this migration adds exactly those.

``years_of_experience`` is published. It is not the establishment's age: a
baker with fifteen years behind a counter who opened their own place last year
has both numbers, and the buyer cares about the fifteen.

``owner_relation`` is not published, and that is the point of it being an
enum on the business rather than free text anywhere else. Owner, manager or
employee answers a reviewer's question —— is this person entitled to list on
behalf of this establishment —— so it reaches the owner and an administrator
and stops there. It sits per *business* rather than per account because one
person may own one place and manage another.

Guarded the same way the earlier migrations here are: a schema that already
ran ahead of its recorded version must still reconcile to head rather than
crash on DuplicateColumn.

Revision ID: a3c9e5b71f28
Revises: d2f6a3c81b47
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a3c9e5b71f28"
down_revision = "d2f6a3c81b47"
branch_labels = None
depends_on = None

_RELATIONS = ("OWNER", "MANAGER", "WORKER")


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    sa.Enum(*_RELATIONS, name="owner_relation").create(bind, checkfirst=True)

    if not _has_column("businesses", "years_of_experience"):
        op.add_column(
            "businesses", sa.Column("years_of_experience", sa.Integer(), nullable=True)
        )
    if not _has_column("businesses", "owner_relation"):
        op.add_column(
            "businesses",
            sa.Column(
                "owner_relation",
                postgresql.ENUM(*_RELATIONS, name="owner_relation", create_type=False),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("businesses", "owner_relation"):
        op.drop_column("businesses", "owner_relation")
    if _has_column("businesses", "years_of_experience"):
        op.drop_column("businesses", "years_of_experience")
    # Dropped after the column that uses it, and only then: the type is
    # unreferenced at this point, so this cannot fail on a dependency.
    sa.Enum(*_RELATIONS, name="owner_relation").drop(op.get_bind(), checkfirst=True)
