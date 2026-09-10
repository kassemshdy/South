"""Service requests: a visitor asks a talent profile to do a piece of work.

The counterpart to :mod:`app.models.order`, and it exists for the same
reason. A product got a persisted request that reaches the owner's
dashboard; a craftsperson got a WhatsApp link, which is fire-and-forget --
unsent, or sent and lost in a busy inbox, it leaves no record and the person
cannot come back to it. The asymmetry was in the data model, not the screen:
``Order.business_id`` points at ``businesses.id``, and a talent profile is
not a business.

Deliberately **not** an ``Order`` with a second nullable parent:

- An order is a basket of catalogue lines, snapshotted because a price can
  change under the customer. A talent profile has no catalogue -- the request
  *is* the description of the work -- so every line-item column would be
  permanently null on half the table, and ``lines`` would have to stop being
  required for one half of it.
- A nullable ``business_id`` would weaken the one rule the orders table
  currently states in the schema itself: an order has exactly one owner who
  has to fulfil it.

What is shared is deliberate: :class:`~app.models.enums.OrderStatus`, because
"new / contacted / done" is the same three-step the same person works
through, and a second enum with identical members would only invite the two
to drift.

The requester's name and phone belong to somebody who never signed up for
anything. They exist so the person can be answered, and they are absent from
every administrator payload -- nothing in moderation needs to know who asked
whom for what.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.talent import TalentProfile


class ServiceRequest(Base, TimestampMixin):
    __tablename__ = "service_requests"
    __table_args__ = (
        # The list is (this profile, newest first), usually filtered to the
        # ones not dealt with yet -- same access pattern as orders.
        Index("ix_service_requests_profile_status", "profile_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    # Required, unlike an order's optional note: an order carries line items
    # that say what is wanted, and this carries nothing else. A request with
    # no description is not a request, it is a phone number.
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, "order_status"), nullable=False, default=OrderStatus.NEW
    )

    profile: Mapped[TalentProfile] = relationship(back_populates="service_requests")
