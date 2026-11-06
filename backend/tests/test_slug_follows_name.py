"""A renamed shop moves to the address its new name makes, and the old
address still reaches it (the owners' request, 6 Nov 2026)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.services.slug import slugify_name
from tests.samples import ar
from tests.test_views import approved_business, owner_headers  # noqa: F401


def test_a_rename_moves_the_address_and_keeps_the_old_one(
    client: TestClient,
    db: Session,
    approved_business: Business,  # noqa: F811
    owner_headers: dict[str, str],  # noqa: F811
) -> None:
    old = approved_business.slug
    new_name = ar("business.sweets_shop")
    updated = client.put(
        f"/api/businesses/{approved_business.id}",
        headers=owner_headers,
        json={"name": new_name},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["slug"] == slugify_name(new_name) != old

    # The new address and the old one both answer, with the current slug.
    assert client.get(f"/api/businesses/{slugify_name(new_name)}").json()["name"] == new_name
    by_old = client.get(f"/api/businesses/{old}")
    assert by_old.status_code == 200, by_old.text
    assert by_old.json()["slug"] == slugify_name(new_name)

    # Saving again with the same name changes nothing.
    again = client.put(
        f"/api/businesses/{approved_business.id}",
        headers=owner_headers,
        json={"name": new_name},
    )
    assert again.json()["slug"] == slugify_name(new_name)

    # Renaming back takes the old address again, and it stops being an alias.
    back = client.put(
        f"/api/businesses/{approved_business.id}",
        headers=owner_headers,
        json={"name": ar("business.manakish")},
    )
    assert back.json()["slug"] == old


def test_another_shop_never_takes_an_old_address(
    client: TestClient,
    db: Session,
    approved_business: Business,  # noqa: F811
    owner_headers: dict[str, str],  # noqa: F811
    category: object,
    location: object,
) -> None:
    old = approved_business.slug
    client.put(
        f"/api/businesses/{approved_business.id}",
        headers=owner_headers,
        json={"name": ar("business.sweets_shop")},
    )
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(approved_business.category_id),
            "location_id": str(approved_business.location_id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["slug"] != old
