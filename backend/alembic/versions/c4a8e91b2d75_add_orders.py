"""Add orders and order_lines

An order request: a visitor collects items and asks the owner to get in
touch (#39). Not e-commerce -- no payment, shipping or stock.

The line items snapshot title, price and currency, because a price can
change and a product can be deleted, and neither may rewrite what a
customer asked for. ``item_id`` is therefore nullable with ON DELETE SET
NULL rather than CASCADE.

Revision ID: c4a8e91b2d75
Revises: b7e4d2f81a06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c4a8e91b2d75"
down_revision = "b7e4d2f81a06"
branch_labels = None
depends_on = None

STATUSES = ("NEW", "CONTACTED", "DONE")

# `create_type=False` is honoured by the postgresql dialect's ENUM and
# ignored by the generic sa.Enum, which then emits a second CREATE TYPE from
# create_table and dies on DuplicateObject.
_status_column = postgresql.ENUM(*STATUSES, name="order_status", create_type=False)
_status_type = postgresql.ENUM(*STATUSES, name="order_status")
# `currency` already exists -- business_items uses it -- so it is only ever
# referenced here, never created and never dropped.
_currency_column = postgresql.ENUM(name="currency", create_type=False)


def upgrade() -> None:
    _status_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_name", sa.String(length=80), nullable=False),
        sa.Column("customer_phone", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", _status_column, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_orders_business_id_businesses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
    )
    op.create_index("ix_orders_business_id", "orders", ["business_id"])
    op.create_index("ix_orders_business_status", "orders", ["business_id", "status"])

    op.create_table(
        "order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", _currency_column, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_order_lines_order_id_orders", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["business_items.id"],
            name="fk_order_lines_item_id_business_items",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_lines"),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_business_status", table_name="orders")
    op.drop_index("ix_orders_business_id", table_name="orders")
    op.drop_table("orders")
    _status_type.drop(op.get_bind(), checkfirst=True)
