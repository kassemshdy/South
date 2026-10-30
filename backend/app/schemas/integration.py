from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ShopifyConnectionStatus


class ShopifyInstallIn(BaseModel):
    shop: str = Field(min_length=1, max_length=255)


class ShopifyInstallOut(BaseModel):
    authorize_url: str


class SubdomainIn(BaseModel):
    subdomain: str = Field(min_length=2, max_length=63)


class ShopifyStatusOut(BaseModel):
    """The owner's own view of their store's connection. Never the token."""

    connected: bool
    # Shopify cannot create stores by API: a shop without one signs up here.
    signup_url: str
    subdomains_available: bool
    subdomain_base: str
    shop_domain: str | None = None
    status: ShopifyConnectionStatus | None = None
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
