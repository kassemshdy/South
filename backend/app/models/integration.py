"""Third-party commerce: a shop's own Shopify store, and partners reading our feed.

The Shopify side lives in the **Shopify Connector**, a separate service
shared by every website that sells this way (one Shopify app, many sites).
Janoubona holds no Shopify or Cloudflare credential: it tells the connector
what its products are and keeps a mirror of what the connector reports back
through signed webhooks.

- ``StoreLink`` -- one per business: the connector's last word on its store.
- ``ItemLink`` -- one per product the connector was told about, with the
  ``buy_url`` it reported.
- ``IntegrationOutbox`` -- pushes to the connector waiting to be sent,
  written in the same transaction as the edit that caused them.
- ``ApiPartner`` -- a company holding a key to the read-only partner feed.
  Named apart from ``PartnerRequest``, the "support the project" form.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.business import Business, BusinessItem

CONNECTED = "CONNECTED"


class StoreLink(Base, TimestampMixin):
    __tablename__ = "store_links"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # PENDING, CONNECTED or UNINSTALLED, as the connector reports it.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    shop_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storefront_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    subdomain: Mapped[str | None] = mapped_column(String(63), nullable=True)
    subdomain_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped[Business] = relationship(back_populates="store_link")

    @property
    def is_live(self) -> bool:
        return self.status == CONNECTED


class ItemLink(Base, TimestampMixin):
    __tablename__ = "item_links"

    id: Mapped[uuid.UUID] = uuid_pk()
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_items.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # QUEUED, SYNCED, SKIPPED or FAILED, as the connector reports it.
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    buy_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped[BusinessItem] = relationship(back_populates="item_link")


class IntegrationOutbox(Base, TimestampMixin):
    __tablename__ = "integration_outbox"
    __table_args__ = (Index("ix_integration_outbox_pending", "done_at", "next_attempt_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiPartner(Base, TimestampMixin):
    __tablename__ = "api_partners"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # The first characters of the key, shown in the admin list so a key
    # can be recognised without being stored.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Space-separated: "stores:read products:read".
    scopes: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def scope_set(self) -> frozenset[str]:
        return frozenset(self.scopes.split())
