"""mark each product as made in the South or imported

A shop that sells both registers once, and each of its goods is shown under
the door that describes it -- the CEO's answer to how a mixed shop should
appear. So the mark moves down to the product, and the shop's own mark
becomes the door it came through and the default its new products take.

Backfilled from the shop, not left at the server default, so a shop already
marked imported keeps its goods under the imported door.

Revision ID: d4a8f2c61e57
Revises: c7e2d9a4b813
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d4a8f2c61e57"
down_revision = "c7e2d9a4b813"
branch_labels = None
depends_on = None

_ORIGINS = ("LOCAL", "IMPORTED")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # The type already exists: the shop's column created it.
    sa.Enum(*_ORIGINS, name="goods_origin").create(op.get_bind(), checkfirst=True)
    if not _has_column("business_items", "goods_origin"):
        op.add_column(
            "business_items",
            sa.Column(
                "goods_origin",
                postgresql.ENUM(*_ORIGINS, name="goods_origin", create_type=False),
                nullable=False,
                server_default="LOCAL",
            ),
        )
        op.execute(
            "UPDATE business_items SET goods_origin = businesses.goods_origin "
            "FROM businesses WHERE businesses.id = business_items.business_id"
        )


def downgrade() -> None:
    # The type stays: the shop's column still uses it.
    if _has_column("business_items", "goods_origin"):
        op.drop_column("business_items", "goods_origin")
