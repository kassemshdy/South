"""Suggestions while someone types in the search box.

Each kind is found by the directories' own public search -- the same
approved-only queries and the same Arabic folding (``normalize_arabic``),
so a suggestion is always something the results page would show, and
«مناقيش» finds «مناقيش» however the hamza or the taa marbuta was typed.
Categories are a short table, matched in Python with the same folding.

The query string is dropped from the access log like every other
(``DropQueryString``), so what people type is not written anywhere.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.arabic import normalize_arabic
from app.core.dependencies import DbSession
from app.repositories.business import BusinessRepository
from app.repositories.item import ItemRepository
from app.repositories.talent import TalentRepository
from app.repositories.taxonomy import CategoryRepository

router = APIRouter(prefix="/search", tags=["search"])

#: Fewer than this many letters suggest nothing: one letter matches half
#: the directory.
MIN_LENGTH = 2

LIMITS = {"category": 3, "product": 5, "shop": 4, "service": 3}


class Suggestion(BaseModel):
    kind: Literal["category", "product", "shop", "service"]
    label: str
    slug: str
    image_url: str | None = None
    #: A second line: the shop of a product, the category of a shop.
    detail: str | None = None


@router.get("/suggest", response_model=list[Suggestion])
def suggest(
    db: DbSession, q: Annotated[str, Query(max_length=100)] = ""
) -> list[Suggestion]:
    term = q.strip()
    if len(term) < MIN_LENGTH:
        return []
    folded = normalize_arabic(term)
    out: list[Suggestion] = []

    categories = [
        category
        for category in CategoryRepository(db).list_all()
        if folded in normalize_arabic(category.name_ar)
    ]
    out += [
        Suggestion(kind="category", label=category.name_ar, slug=category.slug)
        for category in categories[: LIMITS["category"]]
    ]

    products = ItemRepository(db).search_public(q=term, page_size=LIMITS["product"]).items
    out += [
        Suggestion(
            kind="product",
            label=item.title,
            slug=item.slug,
            image_url=item.image_url,
            detail=item.business.name if item.business else None,
        )
        for item in products
        if item.slug
    ]

    shops = BusinessRepository(db).search_public(q=term, page_size=LIMITS["shop"]).items
    out += [
        Suggestion(
            kind="shop",
            label=business.name,
            slug=business.slug,
            image_url=business.logo_url,
            detail=business.category.name_ar if business.category else None,
        )
        for business in shops
    ]

    people = TalentRepository(db).search_public(q=term, page_size=LIMITS["service"]).items
    out += [
        Suggestion(
            kind="service",
            label=profile.display_name,
            slug=profile.slug,
            image_url=profile.photo_url,
            detail=profile.skill.name_ar if profile.skill else None,
        )
        for profile in people
    ]
    return out
