"""Order requests: a visitor places one, the owner works through it.

Two routers, and the split is the privacy boundary. The public route only
ever *writes*; there is no public and no administrator read, because an
order carries a third party's name and phone number and the only person
with a reason to see it is the owner who has to reply.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core.dependencies import AppSettings, ClientIp, DbSession, OwnedBusiness
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.repositories.business import BusinessRepository
from app.repositories.order import OrderRepository
from app.schemas.common import MessageResponse
from app.schemas.order import OrderCreateIn, OrderOut, OrderStatusIn
from app.services.order import OrderService

public_router = APIRouter(tags=["orders"])
owner_router = APIRouter(tags=["my-orders"])


# --- Public ----------------------------------------------------------------


@public_router.post(
    "/businesses/{slug}/orders",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    slug: Annotated[str, Path(max_length=200)],
    payload: OrderCreateIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    """Ask an approved listing's owner to get in touch about some items.

    Answers with a message rather than the stored order: there is nothing a
    visitor can do with an id, and echoing one back would be the only way
    this endpoint could report anything about the owner's dashboard.
    """
    business = BusinessRepository(db).get_by_slug(slug, public_only=True)
    if business is None:
        raise NotFoundError("business.not_public")

    OrderService(db, settings).place(business, payload, client_ip=client_ip)
    return MessageResponse(message=translate("order.received"))


# --- Owner -----------------------------------------------------------------


@owner_router.get("/businesses/{business_id}/orders", response_model=list[OrderOut])
def list_my_orders(
    business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> list[OrderOut]:
    """Orders on the caller's listing, newest first."""
    return [
        OrderOut.model_validate(order)
        for order in OrderService(db, settings).for_business(business)
    ]


@owner_router.post(
    "/businesses/{business_id}/orders/{order_id}/status", response_model=OrderOut
)
def set_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusIn,
    business: OwnedBusiness,
    db: DbSession,
    settings: AppSettings,
) -> OrderOut:
    """Move an order along, so the list stays useful rather than a pile."""
    order = OrderRepository(db).owned(order_id, business.id)
    if order is None:
        # 404 rather than 403: this must not confirm that an id exists on
        # some other listing.
        raise NotFoundError("order.not_found")
    return OrderOut.model_validate(
        OrderService(db, settings).set_status(order, payload.status)
    )
