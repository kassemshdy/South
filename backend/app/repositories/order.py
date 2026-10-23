"""Order data access.

No authorization decisions here: ``for_business`` returns what it is asked
for, and establishing that the caller owns that business is the service's
and the dependency's job.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

from app.models.business import Business
from app.models.enums import OrderStatus
from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    def _with_lines(self, stmt: Select[tuple[Order]]) -> Select[tuple[Order]]:
        return stmt.options(selectinload(Order.lines))

    def for_business(self, business_id: uuid.UUID) -> list[Order]:
        """Newest first, with their line items."""
        stmt = self._with_lines(
            select(Order)
            .where(Order.business_id == business_id)
            .order_by(Order.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def owned(self, order_id: uuid.UUID, business_id: uuid.UUID) -> Order | None:
        """Scoped by business id, which is what stops an owner reaching
        another listing's order by swapping the id in the URL."""
        stmt = self._with_lines(
            select(Order).where(Order.id == order_id, Order.business_id == business_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def owned_by_user(self, order_id: uuid.UUID, user_id: uuid.UUID) -> Order | None:
        """An order on any listing the user owns -- the link a customer sends
        carries only the order's id. Scoped by owner for the same reason as
        ``owned``."""
        stmt = self._with_lines(
            select(Order)
            .join(Business, Business.id == Order.business_id)
            .where(Order.id == order_id, Business.owner_id == user_id)
            .options(joinedload(Order.business))
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def recent(self, *, status: OrderStatus | None, limit: int) -> list[Order]:
        """Every listing's orders, newest first, for the administrators."""
        stmt = select(Order).options(joinedload(Order.business))
        if status is not None:
            stmt = stmt.where(Order.status == status)
        stmt = self._with_lines(stmt.order_by(Order.created_at.desc()).limit(limit))
        return list(self.db.execute(stmt).unique().scalars().all())
