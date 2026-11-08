"""The public map of the South: every published shop and service provider
with a pin, for the map-and-chart page (the owners' request, 8 Nov 2026).

Shops are pinned exactly, as on their own pages. A service provider is a
person, so their pin is rounded to about a kilometre -- the area of their
town, never their door, the same rule as their profile page's map.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.core.cache import cached
from app.core.dependencies import DbSession
from app.models.business import Business
from app.models.enums import BusinessStatus, LocationType, TalentKind
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location

router = APIRouter(prefix="/map", tags=["map"])

#: Two decimals of a degree: about 1.1 km north-south here.
SERVICE_PRECISION = 2


class MapListingOut(BaseModel):
    kind: Literal["business", "service"]
    slug: str
    name: str
    #: The shop's category or the provider's skill.
    category: str | None = None
    category_slug: str | None = None
    town: str | None = None
    #: The district the town belongs to, for the per-district chart.
    district: str | None = None
    latitude: float
    longitude: float


def _place(location: Location | None, parent: Location | None) -> tuple[str | None, str | None]:
    """(town, district) for a listing's location, whichever level it is."""
    if location is None:
        return None, None
    if location.type is LocationType.TOWN:
        return location.name_ar, parent.name_ar if parent is not None else None
    if location.type is LocationType.DISTRICT:
        return None, location.name_ar
    return None, None


@router.get("/listings", response_model=list[MapListingOut])
def listings(db: DbSession) -> list[MapListingOut]:
    def build() -> list[MapListingOut]:
        parent = aliased(Location)
        out: list[MapListingOut] = []
        shops = db.execute(
            select(Business, Category, Location, parent)
            .outerjoin(Category, Business.category_id == Category.id)
            .outerjoin(Location, Business.location_id == Location.id)
            .outerjoin(parent, Location.parent_id == parent.id)
            .where(
                Business.status == BusinessStatus.APPROVED,
                Business.latitude.is_not(None),
                Business.longitude.is_not(None),
            )
        ).all()
        for shop, category, location, district in shops:
            town, district_name = _place(location, district)
            out.append(
                MapListingOut(
                    kind="business",
                    slug=shop.slug,
                    name=shop.name,
                    category=category.name_ar if category else None,
                    category_slug=category.slug if category else None,
                    town=town,
                    district=district_name,
                    latitude=float(shop.latitude),
                    longitude=float(shop.longitude),
                )
            )
        people = db.execute(
            select(TalentProfile, TalentSkill, Location, parent)
            .outerjoin(TalentSkill, TalentProfile.skill_id == TalentSkill.id)
            .outerjoin(Location, TalentProfile.location_id == Location.id)
            .outerjoin(parent, Location.parent_id == parent.id)
            .where(
                TalentProfile.status == BusinessStatus.APPROVED,
                TalentProfile.kind == TalentKind.SERVICE,
                TalentProfile.latitude.is_not(None),
                TalentProfile.longitude.is_not(None),
            )
        ).all()
        for profile, skill, location, district in people:
            town, district_name = _place(location, district)
            out.append(
                MapListingOut(
                    kind="service",
                    slug=profile.slug,
                    name=profile.display_name,
                    category=skill.name_ar if skill else None,
                    category_slug=skill.slug if skill else None,
                    town=town,
                    district=district_name,
                    latitude=round(float(profile.latitude), SERVICE_PRECISION),
                    longitude=round(float(profile.longitude), SERVICE_PRECISION),
                )
            )
        return out

    return cached("map:listings", build)
