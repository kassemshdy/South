from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.models.enums import OrderStatus
from app.schemas.common import ORMModel


class ServiceRequestCreateIn(BaseModel):
    """What a visitor sends. No account, so the contact details are the whole
    of what the person has to work with -- hence both are required and the
    phone goes through the same normaliser as every other number here."""

    customer_name: str = Field(min_length=2, max_length=80)
    customer_phone: str = Field(min_length=6, max_length=20)
    # Required, unlike an order's note: there are no line items here, so this
    # is the only place the work being asked for is described.
    details: str = Field(min_length=10, max_length=1000)

    @field_validator("customer_phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("details")
    @classmethod
    def _strip_details(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError(translate("service_request.details_too_short"))
        return cleaned


class ServiceRequestOut(ORMModel):
    """The provider's view. There is no public and no administrator
    counterpart on purpose: a request carries a third party's name and phone
    number, and the only person with a reason to see it is the one who has to
    reply."""

    id: uuid.UUID
    customer_name: str
    customer_phone: str
    details: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class ServiceRequestStatusIn(BaseModel):
    status: OrderStatus
