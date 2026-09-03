"""Products, services and menu items — one model, three presentations."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.business import Business, BusinessItem
from app.schemas.item import BusinessItemIn, BusinessItemUpdateIn

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_BUSINESS = 200


class BusinessItemService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_business(self, business_id: uuid.UUID) -> list[BusinessItem]:
        return list(
            self._db.execute(
                select(BusinessItem)
                .where(BusinessItem.business_id == business_id)
                .order_by(BusinessItem.sort_order, BusinessItem.created_at)
            )
            .scalars()
            .all()
        )

    def get_owned(self, business: Business, item_id: uuid.UUID) -> BusinessItem:
        """Fetch an item, scoped to the business the caller already owns.

        Scoping by business_id here is what stops an owner from editing another
        listing's item by swapping the id in the URL.
        """
        item = self._db.execute(
            select(BusinessItem).where(
                BusinessItem.id == item_id, BusinessItem.business_id == business.id
            )
        ).scalar_one_or_none()
        if item is None:
            raise NotFoundError("item.not_found")
        return item

    def create(self, business: Business, payload: BusinessItemIn) -> BusinessItem:
        count = int(
            self._db.execute(
                select(func.count())
                .select_from(BusinessItem)
                .where(BusinessItem.business_id == business.id)
            ).scalar_one()
        )
        if count >= MAX_ITEMS_PER_BUSINESS:
            raise ValidationError(
                "item.too_many",
                code="too_many_items",
                params={"max": MAX_ITEMS_PER_BUSINESS},
            )

        sort_order = payload.sort_order or count
        item = BusinessItem(
            business_id=business.id,
            title=payload.title,
            description=payload.description,
            price=payload.price,
            currency=payload.currency,
            is_available=payload.is_available,
            sort_order=sort_order,
        )
        self._db.add(item)
        self._db.commit()
        logger.info(
            "Business item created",
            extra={"business_id": str(business.id), "item_id": str(item.id)},
        )
        return item

    def update(self, item: BusinessItem, payload: BusinessItemUpdateIn) -> BusinessItem:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self._db.commit()
        return item

    def delete(self, item: BusinessItem) -> str | None:
        """Remove the item, returning its storage key so the caller can clean up."""
        storage_key = item.image_storage_key
        self._db.delete(item)
        self._db.commit()
        return storage_key

    def reorder(self, business: Business, item_ids: list[uuid.UUID]) -> list[BusinessItem]:
        items = {item.id: item for item in self.list_for_business(business.id)}
        unknown = [item_id for item_id in item_ids if item_id not in items]
        if unknown:
            raise ValidationError("item.unknown_in_order", code="unknown_item")

        for position, item_id in enumerate(item_ids):
            items[item_id].sort_order = position
        self._db.commit()
        return self.list_for_business(business.id)
