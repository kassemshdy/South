"""The growth report: Alex Hormozi's value equation, read off the live data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Lever = Literal["outcome", "likelihood", "time", "effort"]
Priority = Literal["high", "medium", "low"]


class WeeklySeries(BaseModel):
    """One number per seven-day window, oldest first, the current week last."""

    orders: list[int]
    service_requests: list[int]
    views: list[int] = Field(description="Page opens, never people")
    new_sellers: list[int] = Field(description="Shops and service profiles created")
    new_products: list[int]


class SellerHealth(BaseModel):
    """Every approved shop in exactly one bucket, over the last 30 days."""

    with_orders: int
    viewed_no_orders: int
    unseen: int


class ShopLine(BaseModel):
    name: str
    slug: str
    orders: int
    views: int


class Recommendation(BaseModel):
    key: str
    lever: Lever
    priority: Priority
    count: int | None = None


class GrowthReportOut(BaseModel):
    generated_at: datetime
    week_starts: list[date] = Field(description="First UTC day of each weekly window")

    approved_shops: int
    approved_talents: int
    public_products: int
    pending_reviews: int
    pending_over_48h: int

    shops_with_order_7d: int
    shops_with_order_30d: int
    orders_7d: int
    orders_30d: int
    service_requests_30d: int
    views_30d: int
    orders_per_1000_views: float | None
    median_approval_hours: float | None
    approved_testimonials: int
    thin_catalogue_shops: int = Field(
        description="Approved shops with fewer than 3 public products"
    )
    shops_without_logo: int

    goal_usd: int = Field(description="The platform's sales goal, in US dollars")
    order_value_usd: float = Field(
        description="Every order's USD lines, all time: requested, not confirmed sales"
    )
    order_value_usd_30d: float
    order_value_lbp: float = Field(description="LBP lines, kept apart rather than converted")

    weekly: WeeklySeries
    health: SellerHealth
    top_shops: list[ShopLine]
    quiet_shops: list[ShopLine]
    recommendations: list[Recommendation]


DEFAULT_GOAL_USD = 100_000_000


class GrowthPlanOut(BaseModel):
    """The goal and the offer the growth page is built around; ``offer`` is
    null while the site's own default wording stands."""

    goal_usd: int = DEFAULT_GOAL_USD
    offer: str | None = None
    # Whether visitors are shown the offer in a popup. Off until the manager
    # turns it on, so a deploy shows visitors nothing new.
    offer_popup: bool = False


class GrowthPlanIn(BaseModel):
    goal_usd: int = Field(ge=1, le=1_000_000_000_000)
    offer: str | None = Field(default=None, max_length=5000)
    offer_popup: bool = False

    @field_validator("offer", mode="before")
    @classmethod
    def _blank_is_default(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value


class OfferPopupOut(BaseModel):
    """What a visitor's popup shows: nothing while it is switched off, and
    ``offer`` null while the site's own default wording stands."""

    enabled: bool = False
    offer: str | None = None
