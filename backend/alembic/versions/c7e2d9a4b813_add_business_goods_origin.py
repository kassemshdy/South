"""add whether a business offers goods made in the South or imported ones

The offering and the looking-for pages each gain a separate door for
imported goods sold by southern stores, beside the one for what is made,
assembled or produced in the South. The door an owner comes through sets
this column, and the looking-for doors filter on it.

Not null with a server default of ``LOCAL``: every listing that exists today
was accepted under the rule that goods must be made in the South, so local is
what they all are, and no row is left without an answer.

Guarded like the migrations before it, so a schema that already ran ahead of
its recorded version still reconciles to head.

Revision ID: c7e2d9a4b813
Revises: 8bc63d1e4f72
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c7e2d9a4b813"
down_revision = "8bc63d1e4f72"
branch_labels = None
depends_on = None

_ORIGINS = ("LOCAL", "IMPORTED")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    sa.Enum(*_ORIGINS, name="goods_origin").create(op.get_bind(), checkfirst=True)
    if not _has_column("businesses", "goods_origin"):
        op.add_column(
            "businesses",
            sa.Column(
                "goods_origin",
                postgresql.ENUM(*_ORIGINS, name="goods_origin", create_type=False),
                nullable=False,
                server_default="LOCAL",
            ),
        )


def downgrade() -> None:
    if _has_column("businesses", "goods_origin"):
        op.drop_column("businesses", "goods_origin")
    sa.Enum(*_ORIGINS, name="goods_origin").drop(op.get_bind(), checkfirst=True)
