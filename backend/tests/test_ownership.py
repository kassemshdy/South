"""Ownership isolation.

The rule under test: an owner must never be able to reach another owner's
business by substituting an id in the URL. These tests exist because that is
the single most damaging authorization mistake this application could make.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.taxonomy import Category, Location
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


@pytest.fixture
def victim_business(client: TestClient, category: Category, location: Location) -> tuple[str, dict[str, str]]:
    """A business belonging to owner A, plus owner A's auth header."""
    headers = sign_in(client, "03700001")
    response = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first_owner"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03700001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"], headers


@pytest.fixture
def attacker_headers(client: TestClient) -> dict[str, str]:
    return sign_in(client, "03700002")


def test_attacker_cannot_read_another_owners_business(
    client: TestClient, victim_business: tuple[str, dict[str, str]], attacker_headers: dict[str, str]
) -> None:
    business_id, _ = victim_business
    response = client.get(f"/api/businesses/{business_id}/manage", headers=attacker_headers)
    # 404, not 403: the API must not confirm that this id exists.
    assert response.status_code == 404


def test_attacker_cannot_update_another_owners_business(
    client: TestClient, victim_business: tuple[str, dict[str, str]], attacker_headers: dict[str, str]
) -> None:
    business_id, owner_headers = victim_business

    response = client.put(
        f"/api/businesses/{business_id}", headers=attacker_headers, json={"name": ar("business.stolen")}
    )
    assert response.status_code == 404

    unchanged = client.get(f"/api/businesses/{business_id}/manage", headers=owner_headers)
    assert unchanged.json()["name"] == ar("business.first_owner")


def test_attacker_cannot_delete_another_owners_business(
    client: TestClient, victim_business: tuple[str, dict[str, str]], attacker_headers: dict[str, str]
) -> None:
    business_id, owner_headers = victim_business

    assert client.delete(f"/api/businesses/{business_id}", headers=attacker_headers).status_code == 404
    assert client.get(f"/api/businesses/{business_id}/manage", headers=owner_headers).status_code == 200


def test_attacker_cannot_submit_another_owners_business(
    client: TestClient, victim_business: tuple[str, dict[str, str]], attacker_headers: dict[str, str]
) -> None:
    business_id, _ = victim_business
    assert client.post(f"/api/businesses/{business_id}/submit", headers=attacker_headers).status_code == 404


def test_attacker_cannot_manage_another_owners_items(
    client: TestClient, victim_business: tuple[str, dict[str, str]], attacker_headers: dict[str, str]
) -> None:
    business_id, owner_headers = victim_business

    created = client.post(
        f"/api/businesses/{business_id}/items",
        headers=owner_headers,
        json={"title": ar("item.zaatar"), "price": "1.50", "currency": "USD"},
    )
    item_id = created.json()["id"]

    assert client.get(f"/api/businesses/{business_id}/items", headers=attacker_headers).status_code == 404
    assert (
        client.post(
            f"/api/businesses/{business_id}/items", headers=attacker_headers, json={"title": "x"}
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/businesses/{business_id}/items/{item_id}",
            headers=attacker_headers,
            json={"title": ar("business.stolen")},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/businesses/{business_id}/items/{item_id}", headers=attacker_headers
        ).status_code
        == 404
    )


def test_item_ids_are_scoped_to_their_business(
    client: TestClient, category: Category, location: Location
) -> None:
    """An owner of two businesses cannot cross-edit items between them."""
    headers = sign_in(client, "03700003")

    def make(name: str) -> str:
        response = client.post(
            "/api/businesses",
            headers=headers,
            json={
                "name": name,
                "category_id": str(category.id),
                "location_id": str(location.id),
            },
        )
        return response.json()["id"]

    first, second = make(ar("business.first")), make(ar("business.second"))
    item_id = client.post(
        f"/api/businesses/{first}/items", headers=headers, json={"title": ar("item.generic")}
    ).json()["id"]

    # The item belongs to `first`, so addressing it under `second` must fail.
    crossed = client.put(
        f"/api/businesses/{second}/items/{item_id}", headers=headers, json={"title": ar("item.edited")}
    )
    assert crossed.status_code == 404


def test_owner_cannot_reach_the_admin_api(
    client: TestClient, victim_business: tuple[str, dict[str, str]]
) -> None:
    _, owner_headers = victim_business

    for path in (
        "/api/admin/businesses",
        "/api/admin/businesses/pending",
        "/api/admin/stats",
        "/api/admin/users",
        "/api/admin/categories",
    ):
        assert client.get(path, headers=owner_headers).status_code == 403, path


def test_anonymous_cannot_reach_owner_or_admin_endpoints(client: TestClient) -> None:
    assert client.get("/api/my/businesses").status_code == 401
    assert client.get("/api/admin/stats").status_code == 401
    assert client.post("/api/businesses", json={"name": ar("business.unauthenticated")}).status_code == 401


def test_admin_cannot_edit_a_business_through_the_owner_api(
    client: TestClient, admin, victim_business: tuple[str, dict[str, str]]
) -> None:
    """Admins moderate through the admin API, which records an audit trail."""
    business_id, _ = victim_business
    headers = admin_headers(client)

    assert client.put(f"/api/businesses/{business_id}", headers=headers, json={"name": "x"}).status_code == 404


def test_unknown_business_id_returns_404(client: TestClient, attacker_headers: dict[str, str]) -> None:
    assert (
        client.get(f"/api/businesses/{uuid.uuid4()}/manage", headers=attacker_headers).status_code
        == 404
    )


def test_an_administrator_cannot_create_a_listing_of_their_own(
    client: TestClient, admin, category: Category
) -> None:
    """An administrator decides whether a listing is published.

    Owning one puts them on both sides of that decision, so both create
    routes refuse the account outright rather than accepting a submission the
    review queue cannot honestly judge. Enforced once in ``get_listing_owner``
    so a future create route opts in by asking for ``ListingOwner`` rather
    than quietly inheriting the hole.
    """
    headers = admin_headers(client)

    business = client.post(
        "/api/businesses",
        headers=headers,
        json={"name": ar("business.admin_attempt"), "category_id": str(category.id)},
    )
    assert business.status_code == 403
    assert business.json()["error"]["code"] == "admin_account"

    talent = client.post(
        "/api/talent",
        headers=headers,
        json={"display_name": ar("talent.admin_attempt"), "bio": ar("talent.admin_attempt")},
    )
    assert talent.status_code == 403
    assert talent.json()["error"]["code"] == "admin_account"
