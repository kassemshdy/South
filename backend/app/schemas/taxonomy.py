from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import LocationType
from app.schemas.common import ORMModel


class CategoryOut(ORMModel):
    id: uuid.UUID
    name_ar: str
    slug: str
    icon: str | None = None
    sort_order: int
    is_active: bool
    business_count: int = 0


class CategoryIn(BaseModel):
    name_ar: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdateIn(BaseModel):
    name_ar: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int | None = None
    is_active: bool | None = None


class LocationOut(ORMModel):
    id: uuid.UUID
    name_ar: str
    slug: str
    type: LocationType
    parent_id: uuid.UUID | None = None
    sort_order: int
    is_active: bool
    business_count: int = 0


class LocationIn(BaseModel):
    name_ar: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    type: LocationType = LocationType.TOWN
    parent_id: uuid.UUID | None = None
    sort_order: int = 0
    is_active: bool = True


class LocationUpdateIn(BaseModel):
    name_ar: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    type: LocationType | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None
