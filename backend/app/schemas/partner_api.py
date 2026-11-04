"""The partner feed's shapes: public listing data and where to buy.

Built from the public serializers, so nothing reaches a partner that a
visitor could not already read -- and in particular no field of the owner's
identity (``tests/test_partner_api.py`` pins that, beside test_identity.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.models.enums import Currency, GoodsOrigin
from app.schemas.business import BusinessSummaryOut


class PartnerStoreOut(BusinessSummaryOut):
    page_url: str
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    updated_at: datetime
    # The shop's Shopify store; None when it has not connected one.
    shop_domain: str | None = None
    online_store_url: str | None = None
    subdomain_hostname: str | None = None


class PartnerProductOut(BaseModel):
    id: uuid.UUID
    slug: str
    store_slug: str
    title: str
    description: str | None = None
    price: Decimal | None = None
    currency: Currency
    image_url: str | None = None
    images: list[str] = []
    goods_origin: GoodsOrigin
    page_url: str
    buy_url: str | None = None
    updated_at: datetime


T = TypeVar("T")


class PartnerPage(BaseModel, Generic[T]):
    items: list[T]
    # Pass back as ``cursor`` for the next page; None on the last one.
    next_cursor: str | None = None
