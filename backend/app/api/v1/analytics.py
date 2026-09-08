"""What an owner can see about their own listings being looked at.

One endpoint, and it is owner-scoped in the strongest available sense: the
listings it reports on are the ones that came back from a lookup keyed by
the authenticated user's id, so no id from the request is ever used to
reach a listing. That is the pattern ``AGENTS.md`` requires of every
``/api/my/*`` route.

Views are counted on the public detail routes themselves, not here -- see
``app.services.analytics``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.analytics import ListingViewsOut, OwnerViewsOut
from app.services.analytics import RECENT_DAYS, WINDOW_DAYS, ViewCounterService

owner_router = APIRouter(tags=["my-insights"])


@owner_router.get("/my/views", response_model=OwnerViewsOut)
def my_views(user: CurrentUser, db: DbSession) -> OwnerViewsOut:
    """Daily view counts for every listing the caller owns.

    One request for the whole dashboard rather than one per card: the
    counts come back from a single query per subject type.
    """
    listings = ViewCounterService(db).for_owner(user)
    return OwnerViewsOut(
        window_days=WINDOW_DAYS,
        recent_days=RECENT_DAYS,
        listings=[ListingViewsOut.model_validate(listing) for listing in listings],
    )
