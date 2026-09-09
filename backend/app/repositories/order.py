"""Order data access.

No authorization decisions here: ``for_business`` returns what it is asked
for, and establishing that the caller owns that business is the service's
and the dependency's job.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

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
