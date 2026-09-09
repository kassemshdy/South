"""Order requests: a visitor collects items and asks the owner to get in touch.

Explicitly **not e-commerce** -- no payment, no shipping, no stock. The
issue behind it turned on one requirement: the order *appears to the owner*.
So it is stored, not merely composed into a WhatsApp deep link. A link alone
is fire-and-forget -- unsent, or sent and lost in a busy inbox, it leaves no
record and the owner cannot come back to it.

(The requirement is quoted in Arabic on the issue and paraphrased here on
purpose: ``tests/test_i18n.py`` scans docstrings too, so quoting it would
fail the no-Arabic-in-source guard. Which it did, once.)

Three design points, because each is easy to get wrong later:

- **The line items are snapshots, not references.** Title, price and currency
  are copied when the order is placed. A price can change and a product can
  be deleted; neither may silently rewrite what a customer asked for.
  ``item_id`` stays as a nullable link for convenience and is allowed to go
  null.
- **An order belongs to exactly one business**, because one owner has to
  fulfil it.
- **The customer's name and phone belong to a person who never signed up for
  anything.** They exist so the owner can reply, and they are deliberately
  absent from every administrator payload: nothing in moderation needs to
  know who bought what.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import Currency, OrderStatus

if TYPE_CHECKING:
    from app.models.business import Business


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        # The owner's list is (this business, newest first), usually filtered
        # to the ones they have not dealt with yet.
        Index("ix_orders_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, "order_status"), nullable=False, default=OrderStatus.NEW
    )

    business: Mapped[Business] = relationship(back_populates="orders")
    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderLine.created_at",
    )


class OrderLine(Base, TimestampMixin):
    """One item on an order, as it was when the order was placed."""

    __tablename__ = "order_lines"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SET NULL rather than CASCADE: deleting a product must not delete the
    # record that somebody once asked for it.
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("business_items.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        pg_enum(Currency, "currency"), nullable=False, default=Currency.USD
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order: Mapped[Order] = relationship(back_populates="lines")
