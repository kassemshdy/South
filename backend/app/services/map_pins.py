"""Map locations a person should look at, and where each one probably
belongs (the owners' reports and request, 9 Nov 2026).

Two kinds:

- **outside** Lebanon -- saved before pins were checked against the border,
  and shown on no public map (see ``public_pin``);
- **far** -- inside Lebanon but more than ``FAR_PIN_KM`` from the middle of
  its district's other locations. Often a displaced owner who set where
  they live now, so these stay on the map and a person decides.

The town list carries no coordinates, so a suggestion is made from the
other listings: the middle of the trusted locations in the same town, or,
when the town has none, the middle of its district. "Trusted" means inside
Lebanon and not itself far from its district.
"""

from __future__ import annotations

import logging
import math
import statistics
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.pins import in_lebanon
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile
from app.models.taxonomy import Location
from app.schemas.business import BusinessUpdateIn
from app.schemas.talent import TalentUpdateIn
from app.services.business import BusinessService
from app.services.talent import TalentService

logger = logging.getLogger(__name__)

#: A district in the South is about 20-30 km across: further than this from
#: the middle of its own district, a location is in another one.
FAR_PIN_KM = 25
#: A district needs this many locations before its middle means anything.
MIN_DISTRICT_PEERS = 3

Kind = Literal["business", "service"]


@dataclass
class Pin:
    kind: Kind
    id: uuid.UUID
    name: str
    published: bool
    location_id: uuid.UUID | None
    town: str | None
    district: str | None
    latitude: float
    longitude: float
    reason: Literal["outside", "far"] | None = None
    km_from_district: int | None = None
    suggested: tuple[float, float] | None = None
    suggested_from: Literal["town", "district"] | None = None


def km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance on a flat map: accurate to a few percent across Lebanon."""
    return math.hypot(
        (lat1 - lat2) * 111.0, (lng1 - lng2) * 111.0 * math.cos(math.radians(33.6))
    )


def _middle(points: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        round(statistics.median(p[0] for p in points), 5),
        round(statistics.median(p[1] for p in points), 5),
    )


def _all_pins(db: Session) -> list[Pin]:
    district = aliased(Location)
    pins: list[Pin] = []
    sources: tuple[tuple[Kind, type[Business] | type[TalentProfile]], ...] = (
        ("business", Business),
        ("service", TalentProfile),
    )
    for kind, model in sources:
        name_col = Business.name if model is Business else TalentProfile.display_name
        rows = db.execute(
            select(
                model.id,
                name_col,
                model.status,
                model.location_id,
                Location.name_ar,
                # A town's district; a listing placed on a district itself
                # counts with that district.
                func.coalesce(district.name_ar, Location.name_ar),
                model.latitude,
                model.longitude,
            )
            .outerjoin(Location, model.location_id == Location.id)
            .outerjoin(district, Location.parent_id == district.id)
            .where(model.latitude.is_not(None), model.longitude.is_not(None))
        ).all()
        for listing_id, name, status, location_id, town, district_name, lat, lng in rows:
            pins.append(
                Pin(
                    kind=kind,
                    id=listing_id,
                    name=name,
                    published=status == BusinessStatus.APPROVED,
                    location_id=location_id,
                    town=town,
                    district=district_name,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            )
    return pins


def pins_to_check(db: Session) -> list[Pin]:
    """Every location that needs a look, each with a suggestion where one
    can be made. Outside Lebanon first, then furthest first."""
    pins = _all_pins(db)
    inside = [pin for pin in pins if in_lebanon(pin.latitude, pin.longitude)]

    by_district: dict[str, list[tuple[float, float]]] = {}
    for pin in inside:
        if pin.district:
            by_district.setdefault(pin.district, []).append((pin.latitude, pin.longitude))
    district_middle = {
        name: _middle(points)
        for name, points in by_district.items()
        if len(points) >= MIN_DISTRICT_PEERS
    }

    for pin in pins:
        if not in_lebanon(pin.latitude, pin.longitude):
            pin.reason = "outside"
        elif pin.district in district_middle:
            distance = km(pin.latitude, pin.longitude, *district_middle[pin.district])
            if distance > FAR_PIN_KM:
                pin.reason = "far"
                pin.km_from_district = round(distance)

    trusted = [pin for pin in pins if pin.reason is None]
    by_town: dict[uuid.UUID, list[Pin]] = {}
    for pin in trusted:
        if pin.location_id:
            by_town.setdefault(pin.location_id, []).append(pin)
    trusted_by_district: dict[str, list[tuple[float, float]]] = {}
    for pin in trusted:
        if pin.district:
            trusted_by_district.setdefault(pin.district, []).append(
                (pin.latitude, pin.longitude)
            )

    flagged = [pin for pin in pins if pin.reason]
    for pin in flagged:
        town_peers = by_town.get(pin.location_id, []) if pin.location_id else []
        neighbours = [
            (other.latitude, other.longitude) for other in town_peers if other.id != pin.id
        ]
        if neighbours:
            pin.suggested, pin.suggested_from = _middle(neighbours), "town"
        elif (
            pin.district
            and len(trusted_by_district.get(pin.district, [])) >= MIN_DISTRICT_PEERS
        ):
            pin.suggested = _middle(trusted_by_district[pin.district])
            pin.suggested_from = "district"
        if pin.suggested and not in_lebanon(*pin.suggested):
            pin.suggested = pin.suggested_from = None

    flagged.sort(key=lambda pin: (pin.reason != "outside", -(pin.km_from_district or 0)))
    return flagged


def apply_suggestions(db: Session, ids: set[uuid.UUID], staff: str) -> tuple[int, int]:
    """Move each listing in ``ids`` that is still flagged to its suggested
    location, through the same services an owner's edit goes through.
    Returns (moved, skipped): a listing without a suggestion, or no longer
    flagged, is skipped and left as it was."""
    moved = skipped = 0
    for pin in pins_to_check(db):
        if pin.id not in ids:
            continue
        if pin.suggested is None:
            skipped += 1
            continue
        lat, lng = pin.suggested
        if pin.kind == "business":
            business = db.get(Business, pin.id)
            if business is None:
                skipped += 1
                continue
            BusinessService(db).update(business, BusinessUpdateIn(latitude=lat, longitude=lng))
        else:
            profile = db.get(TalentProfile, pin.id)
            if profile is None:
                skipped += 1
                continue
            TalentService(db).update(profile, TalentUpdateIn(latitude=lat, longitude=lng))
        logger.info(
            "Map location moved to its suggestion",
            extra={
                "listing_kind": pin.kind,
                "listing_id": str(pin.id),
                "from": [pin.latitude, pin.longitude],
                "to": [lat, lng],
                "suggested_from": pin.suggested_from,
                "staff": staff,
            },
        )
        moved += 1
    return moved, skipped
