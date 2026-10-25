"""Where a map pin may be: in Lebanon.

The platform lists the South, and every pin is a public answer to "where is
this?". A pin outside the country is a slip of the finger on a zoomed-out
map -- one listing's pin was found in the sea off Haifa -- and it sends
visitors to the wrong place, so it is refused on save rather than published.

The box is Lebanon's with a few kilometres to spare, so a pin on the coast
or the border is never refused for rounding.
"""

from __future__ import annotations

from app.core.i18n import translate

LAT_MIN, LAT_MAX = 33.0, 34.75
LNG_MIN, LNG_MAX = 35.05, 36.7


def in_lebanon(latitude: float, longitude: float) -> bool:
    return LAT_MIN <= latitude <= LAT_MAX and LNG_MIN <= longitude <= LNG_MAX


def check_pin(latitude: float | None, longitude: float | None) -> None:
    """Raise for a pin outside Lebanon; a missing pin is someone else's rule."""
    if latitude is None or longitude is None:
        return
    if not in_lebanon(latitude, longitude):
        raise ValueError(translate("location.pin_outside_lebanon"))
