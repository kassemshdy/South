"""Public category, location and talent-skill endpoints.

All three are database-driven: the frontend renders whatever these return and
has no hardcoded category, town or skill list.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.serializers import category_out, location_out, talent_skill_out
from app.core.dependencies import DbSession
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository, TalentSkillRepository
from app.repositories.taxonomy import CategoryRepository, LocationRepository
from app.schemas.talent import TalentSkillOut
from app.schemas.taxonomy import CategoryOut, LocationOut

router = APIRouter(tags=["taxonomy"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: DbSession) -> list[CategoryOut]:
    """Active categories with the number of approved businesses in each."""
    counts = BusinessRepository(db).public_counts_by_category()
    return [
        out
        for category in CategoryRepository(db).list_all()
        if (out := category_out(category, business_count=counts.get(category.id, 0))) is not None
    ]


@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: DbSession) -> list[LocationOut]:
    """The full location tree; the client groups it by ``type``/``parent_id``."""
    counts = BusinessRepository(db).public_counts_by_location()
    locations = LocationRepository(db).list_all()

    # A district's count includes the towns beneath it, matching how the search
    # filter behaves.
    rollup: dict = dict(counts)
    for location in locations:
        if location.parent_id is not None:
            rollup[location.parent_id] = rollup.get(location.parent_id, 0) + counts.get(
                location.id, 0
            )

    return [
        out
        for location in locations
        if (out := location_out(location, business_count=rollup.get(location.id, 0))) is not None
    ]


@router.get("/talent-skills", response_model=list[TalentSkillOut])
def list_talent_skills(db: DbSession) -> list[TalentSkillOut]:
    """Active talent skills with the number of approved profiles in each."""
    counts = TalentRepository(db).public_counts_by_skill()
    return [
        out
        for skill in TalentSkillRepository(db).list_all()
        if (out := talent_skill_out(skill, talent_count=counts.get(skill.id, 0))) is not None
    ]
