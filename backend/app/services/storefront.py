"""Where a visitor is sent to buy: the shop's own Shopify store.

The only parts of a ``ShopifyConnection`` that reach a public payload, and
only while the connection is live -- an uninstalled app's store may no
longer sell anything, and a link to it would be a dead end.
"""

from __future__ import annotations

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus


def online_store_url(business: Business) -> str | None:
    connection = business.shopify_connection
    if connection is None or not connection.is_live:
        return None
    return f"https://{connection.storefront_host}"


def buy_url(item: BusinessItem) -> str | None:
    link = item.shopify_link
    if link is None or not link.active or not link.handle or not item.is_available:
        return None
    if item.business.status is not BusinessStatus.APPROVED:
        return None
    store = online_store_url(item.business)
    return f"{store}/products/{link.handle}" if store else None
