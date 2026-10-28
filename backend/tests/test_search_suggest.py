"""Search suggestions: what the box offers while someone types."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.taxonomy import Category
from tests.samples import ar
from tests.test_products import (  # noqa: F401
    approved_business_with_items,
    draft_business_with_item,
)


def _suggest(client: TestClient, q: str) -> list[dict[str, str]]:
    response = client.get("/api/search/suggest", params={"q": q})
    assert response.status_code == 200, response.text
    return response.json()


def test_suggestions_are_what_the_directory_would_show(
    client: TestClient,
    approved_business_with_items: str,  # noqa: F811
) -> None:
    title = ar("item.zaatar_local")
    found = _suggest(client, title[:4])
    assert ("product", title) in [(s["kind"], s["label"]) for s in found]
    assert ("shop", ar("business.sweets_shop")) in [(s["kind"], s["label"]) for s in found]
    # The unavailable product is not suggested, as it is not listed.
    assert ar("item.generic") not in [s["label"] for s in _suggest(client, ar("item.generic"))]


def test_a_listing_not_yet_approved_is_never_suggested(
    client: TestClient,
    draft_business_with_item: str,  # noqa: F811
) -> None:
    assert _suggest(client, ar("item.zaatar_local")) == []


def test_categories_match_and_short_queries_suggest_nothing(
    client: TestClient, category: Category
) -> None:
    found = _suggest(client, category.name_ar[:3])
    assert ("category", category.slug) in [(s["kind"], s["slug"]) for s in found]
    assert _suggest(client, category.name_ar[:1]) == []
    assert _suggest(client, "   ") == []
