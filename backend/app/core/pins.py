"""Where a map pin may be: in Lebanon.

The platform lists the South, and every pin is a public answer to "where is
this?". A pin outside the country is a slip of the finger on a zoomed-out
map -- one listing's pin was found in the sea off Haifa -- and it sends
visitors to the wrong place, so it is refused on save rather than published.

A box was not enough: Lebanon's box takes in Upper Galilee, the Golan, a
strip of Syria and the sea, and owners did put pins there (the owners'
ticket, 28 Oct 2026). So a pin must fall inside Lebanon's border itself --
``lebanon_border.json``, the land borders to about 300 m, with the coast
moved about 2 km out so a shop on the shore is never refused. The box stays
as a cheap first test.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from app.core.i18n import translate

LAT_MIN, LAT_MAX = 33.0, 34.75
LNG_MIN, LNG_MAX = 35.05, 36.7

BORDER_FILE = Path(__file__).with_name("lebanon_border.json")


@cache
def _border() -> tuple[tuple[float, float], ...]:
    ring = json.loads(BORDER_FILE.read_text(encoding="utf-8"))["ring"]
    return tuple((float(lng), float(lat)) for lng, lat in ring)


def _inside(longitude: float, latitude: float, ring: tuple[tuple[float, float], ...]) -> bool:
    """Even-odd ray casting: a point is inside if a ray from it crosses the
    border an odd number of times."""
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if (yi > latitude) != (yj > latitude) and longitude < (xj - xi) * (latitude - yi) / (
            yj - yi
        ) + xi:
            inside = not inside
        j = i
    return inside


def in_lebanon(latitude: float, longitude: float) -> bool:
    if not (LAT_MIN <= latitude <= LAT_MAX and LNG_MIN <= longitude <= LNG_MAX):
        return False
    return _inside(longitude, latitude, _border())


def check_pin(latitude: float | None, longitude: float | None) -> None:
    """Raise for a pin outside Lebanon; a missing pin is someone else's rule."""
    if latitude is None or longitude is None:
        return
    if not in_lebanon(latitude, longitude):
        raise ValueError(translate("location.pin_outside_lebanon"))
