"""Shared response shapes."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """The single error envelope returned by every failing endpoint."""

    error: ErrorDetail


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class MessageResponse(BaseModel):
    message: str


class StatsResponse(BaseModel):
    total_businesses: int = Field(description="All businesses regardless of status")
    pending_businesses: int
    approved_businesses: int
    rejected_businesses: int
    suspended_businesses: int
    draft_businesses: int
    total_users: int
    total_admins: int
    total_items: int
    total_talents: int = Field(default=0, description="All talent profiles regardless of status")
    pending_talents: int = 0
    pending_testimonials: int = Field(default=0, description="Testimonials awaiting approval")
    approved_talents: int = 0
    shops_with_products: int = Field(
        default=0,
        description="Approved shops with a visible product (staff only)",
    )


class PublicStatsOut(BaseModel):
    """The homepage stats strip — approved-only, safe for an anonymous visitor.

    The three numbers are the three directories, in the order the browse
    strip lists them. It used to count towns instead of products, which
    measured the map rather than the directory: "3 towns represented" is a
    fact about Lebanon, not about what is in here, and it shrank the site in
    the reader's mind rather than describing it.
    """

    total_businesses: int
    total_products: int = 0
    total_talents: int = 0


class GrowthSeries(BaseModel):
    """Running totals at the end of each day, oldest first."""

    businesses: list[int]
    talents: list[int]
    products: list[int]
    orders: list[int]


class GrowthResponse(BaseModel):
    days: list[date] = Field(description="UTC days, oldest first, today last")
    totals: GrowthSeries



class MapPointOut(BaseModel):
    """One pinned listing on the administrators' map."""

    kind: Literal["business", "service"]
    id: uuid.UUID
    name: str
    status: str
    category: str | None = None
    latitude: float
    longitude: float


class ContactedShopOut(BaseModel):
    """A shop visitors reached through the site -- a press of its WhatsApp or
    call button, or an order -- for staff to ask its owner for a video or a
    testimonial (the owners' request, 9 Nov 2026). Staff-only: it carries the
    owner's account number, as the admin shop payload does."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    contact_clicks: int
    orders: int
    last_contact: date | None = None
    owner_phone: str | None = None


class StrayPinOut(BaseModel):
    """A listing whose map pin falls outside Lebanon -- saved before pins
    were checked -- for staff to move. Hidden from every public map until
    then (see ``public_pin``)."""

    kind: Literal["business", "service"]
    id: uuid.UUID
    name: str
    town: str | None = None
    latitude: float
    longitude: float
    # "outside": across Lebanon's border, hidden from the public maps.
    # "far": inside Lebanon but far from the other pins of its district --
    # often a displaced owner pinned where they live now, so it stays on
    # the map and staff decide (the owners' report, 9 Nov 2026).
    reason: Literal["outside", "far"] = "outside"
    km_from_district: int | None = None
    published: bool = True
    # Where it probably belongs: the middle of the other locations in its
    # town, or of its district when the town has none (see map_pins).
    suggested_latitude: float | None = None
    suggested_longitude: float | None = None
    suggested_from: Literal["town", "district"] | None = None


class StrayPinsApplyIn(BaseModel):
    """The listings to move to their suggested locations."""

    ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class StrayPinsAppliedOut(BaseModel):
    moved: int
    skipped: int
