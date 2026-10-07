"""Ordering by distance from a visitor, for the directories' "nearest" sort."""

from __future__ import annotations

import math

from sqlalchemy import Float, cast, nullslast
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import UnaryExpression

#: A visitor's position as (latitude, longitude), from their browser and only
#: for this one request: it is never stored or logged.
Point = tuple[float, float]


def nearest_first(
    latitude: InstrumentedAttribute[float | None],
    longitude: InstrumentedAttribute[float | None],
    origin: Point,
) -> UnaryExpression[float]:
    """Closest pin first, listings with no pin after every one that has one.

    The squared distance on a plane scaled by the cosine of the visitor's
    latitude: across a region the size of Lebanon it orders exactly as the
    great-circle distance would, needs no extension, and only the order is
    used -- no distance is shown, so none needs to be exact.
    """
    lat0, lng0 = origin
    scale = math.cos(math.radians(lat0))
    north = cast(latitude, Float) - lat0
    east = (cast(longitude, Float) - lng0) * scale
    return nullslast((north * north + east * east).asc())


def point_or_none(latitude: float | None, longitude: float | None) -> Point | None:
    """A position only when both halves were sent."""
    if latitude is None or longitude is None:
        return None
    return (latitude, longitude)
