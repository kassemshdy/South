"""Service requests: a visitor asks a talent profile for work, the provider
works through it.

Two routers, and the split is the privacy boundary -- the same one
``orders.py`` draws. The public route only ever *writes*; there is no public
and no administrator read, because a request carries a third party's name and
phone number and the only person with a reason to see it is the one who has
to reply.

The owner routes carry no profile id: a talent profile is one-per-account, so
``OwnTalentProfile`` resolves it from the authenticated user and there is no
id a caller could substitute to reach someone else's requests.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core.dependencies import AppSettings, ClientIp, DbSession, OwnTalentProfile
from app.core.errors import NotFoundError
from app.core.i18n import translate
from app.repositories.service_request import ServiceRequestRepository
from app.repositories.talent import TalentRepository
from app.schemas.common import MessageResponse
from app.schemas.service_request import (
    ServiceRequestCreateIn,
    ServiceRequestOut,
    ServiceRequestStatusIn,
)
from app.services.service_request import ServiceRequestService

public_router = APIRouter(tags=["service-requests"])
owner_router = APIRouter(tags=["my-service-requests"])


# --- Public ----------------------------------------------------------------


@public_router.post(
    "/talent/{slug}/requests",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_service_request(
    slug: Annotated[str, Path(max_length=200)],
    payload: ServiceRequestCreateIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> MessageResponse:
    """Ask an approved talent profile to do a piece of work.

    Answers with a message rather than the stored request: there is nothing a
    visitor can do with an id, and echoing one back would be the only way
    this endpoint could report anything about the provider's dashboard.
    """
    profile = TalentRepository(db).get_by_slug(slug, public_only=True)
    if profile is None:
        raise NotFoundError("talent.not_public")

    ServiceRequestService(db, settings).place(profile, payload, client_ip=client_ip)
    return MessageResponse(message=translate("service_request.received"))


# --- Owner -----------------------------------------------------------------


@owner_router.get("/my/talent/requests", response_model=list[ServiceRequestOut])
def list_my_service_requests(
    profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> list[ServiceRequestOut]:
    """Requests on the caller's own profile, newest first."""
    return [
        ServiceRequestOut.model_validate(request)
        for request in ServiceRequestService(db, settings).for_profile(profile)
    ]


@owner_router.post(
    "/my/talent/requests/{request_id}/status", response_model=ServiceRequestOut
)
def set_service_request_status(
    request_id: uuid.UUID,
    payload: ServiceRequestStatusIn,
    profile: OwnTalentProfile,
    db: DbSession,
    settings: AppSettings,
) -> ServiceRequestOut:
    """Move a request along, so the list stays useful rather than a pile."""
    request = ServiceRequestRepository(db).owned(request_id, profile.id)
    if request is None:
        # 404 rather than 403: this must not confirm that an id exists on
        # some other profile.
        raise NotFoundError("service_request.not_found")
    return ServiceRequestOut.model_validate(
        ServiceRequestService(db, settings).set_status(request, payload.status)
    )
