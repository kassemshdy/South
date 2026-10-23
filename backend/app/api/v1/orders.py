"""Order requests: a visitor places one, the owner works through it.

Three routers, and the split is the privacy boundary. The public route only
ever *writes*; there is no public read, because an order carries a third
party's name and phone number. The owner reads their listing's orders, and
the administrators read every order (the owners' decision, so they can follow
orders up with the shops).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.core.dependencies import (
    AdminUser,
    AppSettings,
    ClientIp,
    CurrentUser,
    DbSession,
    OwnedBusiness,
)
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.models.enums import OrderStatus
from app.models.order import Order
from app.repositories.business import BusinessRepository
from app.repositories.order import OrderRepository
from app.schemas.order import (
    OrderCreateIn,
    OrderOut,
    OrderPlacedOut,
    OrderStatusIn,
    OrderWithBusinessOut,
)
from app.services.order import OrderService

public_router = APIRouter(tags=["orders"])
owner_router = APIRouter(tags=["my-orders"])
admin_router = APIRouter(prefix="/admin", tags=["admin-orders"])

# Enough to work through by hand; the status filter narrows it.
ADMIN_LIST_LIMIT = 200


def _with_business(order: Order) -> OrderWithBusinessOut:
    return OrderWithBusinessOut.model_validate(
        {
            **OrderOut.model_validate(order).model_dump(),
            "business_id": order.business.id,
            "business_name": order.business.name,
            "business_slug": order.business.slug,
        }
    )


# --- Public ----------------------------------------------------------------


@public_router.post(
    "/businesses/{slug}/orders",
    response_model=OrderPlacedOut,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    slug: Annotated[str, Path(max_length=200)],
    payload: OrderCreateIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> OrderPlacedOut:
    """Ask an approved listing's owner to get in touch about some items.

    Answers with a message and the order's id, never the stored order. The
    id goes into the link the visitor sends the shop on WhatsApp, and opens
    the order only for that shop's owner.
    """
    business = BusinessRepository(db).get_by_slug(slug, public_only=True)
    if business is None:
        raise NotFoundError("business.not_public")

    order = OrderService(db, settings).place(business, payload, client_ip=client_ip)
    return OrderPlacedOut(message=translate("order.received"), order_id=order.id)


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


@owner_router.get("/my/orders/{order_id}", response_model=OrderWithBusinessOut)
def get_my_order(order_id: uuid.UUID, user: CurrentUser, db: DbSession) -> OrderWithBusinessOut:
    """One order, from the link a customer sent. 404 for anyone but the
    owner of its listing, so the link confirms nothing to whoever else
    sees the chat."""
    order = OrderRepository(db).owned_by_user(order_id, user.id)
    if order is None:
        raise NotFoundError("order.not_found")
    return _with_business(order)


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


# --- Administrator -----------------------------------------------------------


@admin_router.get("/orders", response_model=list[OrderWithBusinessOut])
def list_all_orders(
    db: DbSession,
    admin: AdminUser,
    order_status: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> list[OrderWithBusinessOut]:
    """Every listing's orders, newest first. Read-only: the shop replies to
    its customer and moves the order along, not the administrators."""
    return [
        _with_business(order)
        for order in OrderRepository(db).recent(status=order_status, limit=ADMIN_LIST_LIMIT)
    ]
