from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Currency
from app.schemas.common import ORMModel


class BusinessItemOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    price: Decimal | None = None
    currency: Currency
    image_url: str | None = None
    is_available: bool
    sort_order: int


class BusinessItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0, le=Decimal("99999999.99"))
    currency: Currency = Currency.USD
    is_available: bool = True
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("اسم العنصر مطلوب.")
        return cleaned


class BusinessItemUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0, le=Decimal("99999999.99"))
    currency: Currency | None = None
    is_available: bool | None = None
    sort_order: int | None = None


class ItemReorderIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1)
