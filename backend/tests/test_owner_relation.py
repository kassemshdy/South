"""Two fields the seller-profile ticket added to a business, and the one
line that separates them.

``years_of_experience`` is a buyer's trust signal, same footing as
``founding_date``, so it is declared on ``BusinessDetailOut`` — the public
tier — and must reach an anonymous visitor.

``owner_relation`` answers a different question: is the person listing this
establishment its owner, its manager, or someone who works there. That is a
reviewer's question, not a shopper's, so it is declared one class further in,
on ``OwnerBusinessOut``, and must never reach a public payload. Nothing
enforces that boundary except which class the field is declared on — no
runtime check strips it — so a field promoted one class up the inheritance
chain would leak with no other code change and no error. This is the test
that would catch it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _create_business(
    client: TestClient, headers: dict[str, str], category: Category, location: Location
) -> dict:
    return client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03960101",
            "years_of_experience": 12,
            "owner_relation": "MANAGER",
        },
    ).json()


def test_years_of_experience_reaches_an_anonymous_reader(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960101")
    created = _create_business(client, owner_headers, category, location)
    assert created["years_of_experience"] == 12

    business = db.get(Business, created["id"])
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    client.post(f"/api/businesses/{created['id']}/submit", headers=owner_headers)
    client.post(
        f"/api/admin/businesses/{created['id']}/approve", headers=admin_headers(client)
    )

    detail = client.get(f"/api/businesses/{created['slug']}").json()
    assert detail["years_of_experience"] == 12

    listed = client.get("/api/businesses").json()["items"]
    # years_of_experience is not part of the card-sized summary, only the
    # detail payload — the fixture asserts on detail rather than the list.
    assert len(listed) == 1


def test_owner_relation_reaches_the_owner_but_not_an_anonymous_reader(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960102")
    created = _create_business(client, owner_headers, category, location)
    assert created["owner_relation"] == "MANAGER"

    business = db.get(Business, created["id"])
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    client.post(f"/api/businesses/{created['id']}/submit", headers=owner_headers)
    client.post(
        f"/api/admin/businesses/{created['id']}/approve", headers=admin_headers(client)
    )

    # Owner's own manage view: still there.
    managed = client.get(
        f"/api/businesses/{created['id']}/manage", headers=owner_headers
    ).json()
    assert managed["owner_relation"] == "MANAGER"

    # An administrator reviewing the listing sees it too.
    review = client.get(
        f"/api/admin/businesses/{created['id']}", headers=admin_headers(client)
    ).json()
    assert review["owner_relation"] == "MANAGER"

    # The public detail payload and the public list must not carry it at all
    # — not null, absent, the same boundary tests/test_identity.py pins for
    # the account holder's own fields.
    detail = client.get(f"/api/businesses/{created['slug']}").json()
    assert "owner_relation" not in detail

    listed = client.get("/api/businesses").json()["items"][0]
    assert "owner_relation" not in listed


def test_owner_relation_is_optional(
    client: TestClient, category: Category, location: Location
) -> None:
    """The seller-profile form does not force a relation choice; a listing
    created without one is not rejected."""
    owner_headers = sign_in(client, "03960103")
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["owner_relation"] is None


def test_an_unrecognised_relation_is_rejected(
    client: TestClient, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960104")
    response = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "owner_relation": "FOUNDER",
        },
    )
    assert response.status_code == 422, response.text
