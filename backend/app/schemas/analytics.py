from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import ViewSubject
from app.schemas.common import ORMModel


class ListingViewsOut(ORMModel):
    """One listing's view counts over the reporting window.

    ``series`` is dense -- one integer per day of the window, oldest first,
    zeroes included -- because a sparkline drawn from only the non-zero days
    shows a busier listing than the one that exists.
    """

    subject_type: ViewSubject
    subject_id: uuid.UUID
    views_recent: int = Field(description="Views over the recent (shorter) window")
    views_window: int = Field(description="Views over the whole window")
    series: list[int]
    series_start: date


class OwnerViewsOut(BaseModel):
    """Every listing the caller owns, with its numbers.

    The window lengths are returned rather than assumed by the client, so
    the wording on the dashboard ("this week") and the span the numbers
    actually cover cannot drift apart.
    """

    window_days: int
    recent_days: int
    listings: list[ListingViewsOut]
