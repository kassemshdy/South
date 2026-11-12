from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ShopifyInstallIn(BaseModel):
    shop: str = Field(min_length=1, max_length=255)


class ShopifyShopOut(BaseModel):
    """One approved shop in the admin page's picker."""

    id: uuid.UUID
    name: str
    slug: str
    # For the page's "view as the owner" button (the owner's request, 5 Nov
    # 2026); staff only, like the rest of this route.
    owner_id: uuid.UUID
    status: str | None = None
    shop_domain: str | None = None


class ShopifyInstallOut(BaseModel):
    authorize_url: str


class ShopifySetupIn(BaseModel):
    """The delivery rate an administrator sets for a shop's store, shown in its checkout."""

    rate_name: str = Field(default="Standard Delivery", min_length=1, max_length=60)
    price: Decimal = Field(ge=0, le=10000, decimal_places=2)
    description: str | None = Field(default=None, max_length=120)


class SubdomainIn(BaseModel):
    subdomain: str = Field(min_length=2, max_length=63)


class ShopifySetupOut(BaseModel):
    """What the last store setup did, as the connector reported it."""

    at: datetime | None = None
    ok: bool = False
    store_currency: str | None = None
    currency_ok: bool = False
    missing_scopes: list[str] = Field(default_factory=list)
    market_action: str | None = None
    market_name: str | None = None
    market_active: bool = False
    rate_action: str | None = None
    rate_name: str | None = None

    @classmethod
    def from_report(cls, report: dict[str, Any] | None) -> ShopifySetupOut | None:
        if not isinstance(report, dict):
            return None
        raw_market, raw_rate = report.get("market"), report.get("rate")
        market: dict[str, Any] = raw_market if isinstance(raw_market, dict) else {}
        rate: dict[str, Any] = raw_rate if isinstance(raw_rate, dict) else {}
        return cls(
            at=report.get("at"),
            ok=bool(report.get("ok")),
            store_currency=report.get("store_currency"),
            currency_ok=bool(report.get("currency_ok")),
            missing_scopes=[str(s) for s in report.get("missing_scopes") or []],
            market_action=market.get("action"),
            market_name=market.get("name"),
            market_active=bool(market.get("active")),
            rate_action=rate.get("action"),
            rate_name=rate.get("name"),
        )


class ShopifyStatusOut(BaseModel):
    """The owner's own view of their store's connection. Never the token."""

    connected: bool
    # Shopify cannot create stores by API: a shop without one signs up here.
    signup_url: str | None = None
    subdomains_available: bool
    subdomain_base: str = ""
    shop_domain: str | None = None
    status: str | None = None
    storefront_url: str | None = None
    currency: str | None = None
    subdomain: str | None = None
    subdomain_hostname: str | None = None
    # True once the store answers on our subdomain, i.e. the owner did the
    # one step in Shopify that we cannot do for them.
    subdomain_live: bool = False
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    synced_products: int = 0
    pending_pushes: int = 0
    setup: ShopifySetupOut | None = None


class SyncQueuedOut(BaseModel):
    queued: int


# --- Partner API ------------------------------------------------------------


class ApiPartnerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["stores:read", "products:read"])


class ApiPartnerOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    active: bool
    created_at: datetime
    last_used_at: datetime | None = None


class ApiPartnerIssuedOut(ApiPartnerOut):
    # Shown once; only its hash is kept.
    api_key: str
