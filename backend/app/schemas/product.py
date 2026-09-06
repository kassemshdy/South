"""Public product/service schemas — the independent `/items` surface.

Kept separate from `app/schemas/item.py`, which is the owner-facing shape
nested under a business the caller already owns.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from app.models.enums import Currency
from app.schemas.common import ORMModel
from app.schemas.taxonomy import CategoryOut, LocationOut


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
    business: ProductBusinessRef


class ProductDetailOut(ProductSummaryOut):
    description: str | None = None
    created_at: datetime
