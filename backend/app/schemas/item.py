from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.i18n import translate
from app.models.enums import Currency
from app.schemas.common import ORMModel


class ItemImageOut(ORMModel):
    id: uuid.UUID
    url: str
    caption: str | None = None
    sort_order: int
    width: int | None = None
    height: int | None = None


class BusinessItemOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    price: Decimal | None = None
    currency: Currency
    image_url: str | None = None
    is_available: bool
    sort_order: int
    good_type: str | None = None
    brand_name: str | None = None
    ingredients: str | None = None
    manufactured_at: date | None = None
    expiry_date: date | None = None
    net_weight: str | None = None
    external_link: str | None = None
    images: list[ItemImageOut] = Field(default_factory=list)


class BusinessItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0, le=Decimal("99999999.99"))
    currency: Currency = Currency.USD
    is_available: bool = True
    sort_order: int = 0
    good_type: str | None = Field(default=None, max_length=160)
    brand_name: str | None = Field(default=None, max_length=160)
    ingredients: str | None = Field(default=None, max_length=2000)
    manufactured_at: date | None = None
    expiry_date: date | None = None
    net_weight: str | None = Field(default=None, max_length=80)
    external_link: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(translate("item.title_required"))
        return cleaned


class BusinessItemUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0, le=Decimal("99999999.99"))
    currency: Currency | None = None
    is_available: bool | None = None
    sort_order: int | None = None
    good_type: str | None = Field(default=None, max_length=160)
    brand_name: str | None = Field(default=None, max_length=160)
    ingredients: str | None = Field(default=None, max_length=2000)
    manufactured_at: date | None = None
    expiry_date: date | None = None
    net_weight: str | None = Field(default=None, max_length=80)
    external_link: str | None = Field(default=None, max_length=500)


class ItemReorderIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1)
