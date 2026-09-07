"""Shapes for the seed content, which lives in ``scripts/data/*.json``.

Content is kept out of source: the JSON files are editable by anyone without
touching Python, and no human-language text lives in code. The TypedDicts below
document the expected shape, and :func:`load` fails loudly on a malformed file
rather than seeding something half-formed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class CategorySeed(TypedDict):
    name_ar: str
    slug: str
    icon: str
    sort_order: int


class LocationSeed(TypedDict, total=False):
    name_ar: str
    slug: str
    children: list[LocationSeed]


class ItemSeed(TypedDict, total=False):
    title: str
    description: str
    price: str
    is_available: bool


class BusinessSeed(TypedDict, total=False):
    name: str
    owner_phone: str
    category: str
    location: str
    status: str
    short_description: str
    description: str
    phone: str
    whatsapp: str
    address_text: str
    rejection_reason: str
    suspension_reason: str
    slug: str
    socials: dict[str, str]
    items: list[ItemSeed]


class TalentSkillSeed(TypedDict):
    name_ar: str
    slug: str
    icon: str
    sort_order: int


class TalentSeed(TypedDict, total=False):
    display_name: str
    owner_phone: str
    skill: str
    custom_skill_text: str
    location: str
    status: str
    headline: str
    bio: str
    years_experience: int
    highest_degree: str
    specialization: str
    university: str
    experience: str
    skills_text: str
    services_offered: str
    languages: list[dict[str, str]]
    phone: str
    whatsapp: str
    website: str
    rejection_reason: str
    suspension_reason: str
    slug: str


DATA_DIR = Path(__file__).resolve().parent / "data"

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "categories": ("name_ar", "slug", "sort_order"),
    "locations": ("name_ar", "slug"),
    "businesses": ("name", "owner_phone", "category", "location", "status"),
    "talent_skills": ("name_ar", "slug", "sort_order"),
    "talents": ("display_name", "owner_phone", "skill", "location", "status"),
}


def _load(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Seed data file is missing: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path.name} must contain a non-empty list")

    required = REQUIRED_FIELDS[name]
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ValueError(f"{path.name}[{index}] must be an object")
        missing = [key for key in required if key not in entry]
        if missing:
            raise ValueError(f"{path.name}[{index}] is missing: {', '.join(missing)}")

    return payload


CATEGORIES: list[CategorySeed] = _load("categories")  # type: ignore[assignment]
LOCATIONS: list[LocationSeed] = _load("locations")  # type: ignore[assignment]
BUSINESSES: list[BusinessSeed] = _load("businesses")  # type: ignore[assignment]
TALENT_SKILLS: list[TalentSkillSeed] = _load("talent_skills")  # type: ignore[assignment]
TALENTS: list[TalentSeed] = _load("talents")  # type: ignore[assignment]
