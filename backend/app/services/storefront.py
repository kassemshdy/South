"""Where a visitor is sent to buy: the shop's own Shopify store.

Read from the mirror of what the Shopify Connector reported
(``StoreLink`` / ``ItemLink``), and only while the store is connected -- an
uninstalled app's store may no longer sell anything, and a link to it would
be a dead end.
"""

from __future__ import annotations

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus


def online_store_url(business: Business) -> str | None:
    link = business.store_link
    if link is None or not link.is_live:
        return None
    return link.storefront_url


def buy_url(item: BusinessItem) -> str | None:
    link = item.item_link
    if link is None or not link.active or not link.buy_url or not item.is_available:
        return None
    if item.business.status is not BusinessStatus.APPROVED:
        return None
    return link.buy_url if online_store_url(item.business) else None
