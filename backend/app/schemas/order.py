from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_phone
from app.models.enums import Currency, OrderStatus
from app.schemas.common import ORMModel


class OrderLineIn(BaseModel):
    item_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=99)


class OrderCreateIn(BaseModel):
    """What a visitor sends. No account, so the contact details are the whole
    of what the owner has to work with -- hence both are required and the
    phone goes through the same normaliser as every other number here."""

    customer_name: str = Field(min_length=2, max_length=80)
    customer_phone: str = Field(min_length=6, max_length=20)
    note: str | None = Field(default=None, max_length=1000)
    # One business per order is enforced by the route (the items are checked
    # against the listing in the path), and the cap stops a single request
    # from being a denial-of-service shaped payload.
    lines: list[OrderLineIn] = Field(min_length=1, max_length=50)

    @field_validator("customer_phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)


class OrderLineOut(ORMModel):
    """A line as it was when the order was placed, not as the product is now."""

    title: str
    price: Decimal | None = None
    currency: Currency
    quantity: int


class OrderOut(ORMModel):
    """The owner's view. There is no public or admin counterpart on purpose:
    an order carries a third party's name and phone number, and the only
    person with a reason to see it is the owner who has to reply."""

    id: uuid.UUID
    customer_name: str
    customer_phone: str
    note: str | None = None
    status: OrderStatus
    lines: list[OrderLineOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OrderStatusIn(BaseModel):
    status: OrderStatus
