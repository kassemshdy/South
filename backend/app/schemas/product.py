"""Public product/service schemas — the independent `/items` surface.

Kept separate from `app/schemas/item.py`, which is the owner-facing shape
nested under a business the caller already owns.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, computed_field

from app.models.enums import Currency, GoodsOrigin
from app.schemas.common import ORMModel
from app.schemas.item import ItemImageOut
from app.schemas.taxonomy import CategoryOut, LocationOut
from app.services.images import thumbnail_url


class ProductBusinessRef(ORMModel):
    """Just enough of the parent business for a product card/page to link back."""

    name: str
    slug: str
    phone: str | None = None
    whatsapp: str | None = None
    category: CategoryOut | None = None
    location: LocationOut | None = None


class ProductSummaryOut(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    price: Decimal | None = None
    currency: Currency
    image_url: str | None = None
    goods_origin: GoodsOrigin = GoodsOrigin.LOCAL
    business: ProductBusinessRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_thumb_url(self) -> str | None:
        return thumbnail_url(self.image_url)


class ProductDetailOut(ProductSummaryOut):
    description: str | None = None
    created_at: datetime
    good_type: str | None = None
    brand_name: str | None = None
    ingredients: str | None = None
    manufactured_at: date | None = None
    expiry_date: date | None = None
    net_weight: str | None = None
    external_link: str | None = None
    images: list[ItemImageOut] = Field(default_factory=list)
