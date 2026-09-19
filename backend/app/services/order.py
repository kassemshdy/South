"""Placing an order request, and the owner working through it.

The decisions recorded on the issue, in the order they matter:

- **Anonymous, rate limited.** A junk order costs the owner one message and
  a row to mark handled -- no money, no stock, no delivery, because this is
  explicitly not e-commerce. Against that, a sign-in would sit between a
  real customer and the single action the feature exists to produce. The
  phone number is also checked by the owner using it, which is a weaker
  guarantee than verification and a far cheaper one.
- **No notification.** There is no email infrastructure here and Twilio
  costs per message, so nothing pings the owner in this slice and no string
  claims otherwise. The order is in the dashboard and the buyer gets the
  WhatsApp handoff; the usual path is the customer messaging the owner
  directly, with the difference that the request is now also recorded.
- **No administrator view.** An order carries a third party's name and
  phone. Moderation needs neither, so no admin payload carries an order.

Every line is validated against the listing in the path *and* against what
a visitor is allowed to see, so an order cannot name another shop's product,
an unavailable one, or one belonging to a listing that is not approved.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import RateLimitedError, ValidationError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.business import Business
from app.models.enums import OrderStatus
from app.models.order import Order, OrderLine
from app.repositories.item import ItemRepository
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreateIn


class OrderService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._repo = OrderRepository(db)
        self._items = ItemRepository(db)
        self._limiter = DatabaseRateLimiter(db)
        self._ip_rule = RateLimitRule(
            bucket="order_place_ip",
            limit=settings.order_per_ip_limit,
            window_seconds=settings.order_per_ip_window_seconds,
        )
        self._business_rule = RateLimitRule(
            bucket="order_place_business",
            limit=settings.order_per_business_limit,
            window_seconds=settings.order_per_business_window_seconds,
        )

    def for_business(self, business: Business) -> list[Order]:
        return self._repo.for_business(business.id)

    def place(
        self,
        business: Business,
        payload: OrderCreateIn,
        *,
        client_ip: str | None,
    ) -> Order:
        # Per-business first: it protects the person who would otherwise have
        # to wade through the flood, and it holds when the sender rotates
        # address.
        business_status = self._limiter.hit(self._business_rule, str(business.id))
        if not business_status.allowed:
            raise RateLimitedError(
                business_status.retry_after_seconds, "order.rate_limited"
            )
        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(ip_status.retry_after_seconds, "order.rate_limited")

        requested = {line.item_id: line.quantity for line in payload.lines}
        available = self._items.public_by_ids(business.id, list(requested))
        if len(available) != len(requested):
            # One 422 for the whole order rather than a partial one: silently
            # dropping a line would have the owner reply about something the
            # customer never asked for, or miss something they did.
            raise ValidationError("order.unknown_item", code="unknown_item")

        order = Order(
            business_id=business.id,
            customer_name=payload.customer_name.strip(),
            customer_phone=payload.customer_phone,
            note=payload.note.strip() if payload.note else None,
            status=OrderStatus.NEW,
            lines=[
                OrderLine(
                    item_id=item.id,
                    # Snapshotted: a later price change or deletion must not
                    # rewrite what the customer asked for.
                    title=item.title,
                    price=item.price,
                    currency=item.currency,
                    quantity=requested[item.id],
                )
                for item in available
            ],
        )
        self._repo.add(order)
        self._db.commit()
        return order

    def set_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        self._db.commit()
        return order
