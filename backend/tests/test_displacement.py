"""Where an owner was displaced from: private, unless they choose to show it.

``pre_displacement_place`` is part of the identity block that
``test_identity.py`` keeps off every public payload. The owners asked for it
to be visible to buyers, and the account page had promised it would not be,
so it is published only through the holder's own opt-in
(``User.show_displacement``) and only as ``displaced_from``. These tests pin
both halves: off by default and absent everywhere, on by choice and present
on the shop, its products and the service profile -- and the directory
filter never finds anyone the badge would not show.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from tests.conftest import post_item, sign_in
from tests.samples import ar

OWNER_PHONE = "03970001"
OTHER_PHONE = "03970002"
PLACE = ar("identity.pre_displacement_place")


def _approved_shop(
    client: TestClient,
    db: Session,
    headers: dict[str, str],
    category: Category,
    location: Location,
    *,
    name: str,
) -> dict[str, str]:
    business = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": name,
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    ).json()
    post_item(
        client,
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": name, "price": "1.00", "currency": "USD"},
    )
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()
    return {"id": business["id"], "slug": business["slug"]}


@pytest.fixture
def displaced_owner(client: TestClient) -> dict[str, str]:
    headers = sign_in(client, OWNER_PHONE)
    saved = client.patch(
        "/api/me",
        headers=headers,
        json={"is_displaced": True, "pre_displacement_place": PLACE},
    )
    assert saved.status_code == 200, saved.text
    return headers


def _public_payloads(client: TestClient, slug: str) -> list[dict[str, object]]:
    """The shop as every public route shows it: page, card, product card."""
    detail = client.get(f"/api/businesses/{slug}").json()
    card = next(b for b in client.get("/api/businesses").json()["items"] if b["slug"] == slug)
    product = client.get("/api/items").json()["items"][0]["business"]
    return [detail, card, product]


def test_off_by_default_so_nobody_is_shown_without_choosing(
    client: TestClient,
    db: Session,
    displaced_owner: dict[str, str],
    category: Category,
    location: Location,
) -> None:
    me = client.get("/api/me", headers=displaced_owner).json()
    assert me["show_displacement"] is False

    shop = _approved_shop(
        client, db, displaced_owner, category, location, name=ar("business.manakish")
    )
    for payload in _public_payloads(client, shop["slug"]):
        assert payload["displaced_from"] is None
        assert "pre_displacement_place" not in payload


def test_shown_on_the_shop_and_its_products_once_the_owner_opts_in(
    client: TestClient,
    db: Session,
    displaced_owner: dict[str, str],
    category: Category,
    location: Location,
) -> None:
    shop = _approved_shop(
        client, db, displaced_owner, category, location, name=ar("business.manakish")
    )
    opted = client.patch("/api/me", headers=displaced_owner, json={"show_displacement": True})
    assert opted.json()["show_displacement"] is True

    for payload in _public_payloads(client, shop["slug"]):
        assert payload["displaced_from"] == PLACE

    # And withdrawn as simply as it was given.
    client.patch("/api/me", headers=displaced_owner, json={"show_displacement": False})
    for payload in _public_payloads(client, shop["slug"]):
        assert payload["displaced_from"] is None


def test_an_opt_in_without_being_displaced_shows_nothing(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """The switch alone publishes nothing: a place left over from an earlier
    answer stays private once the holder says they are no longer displaced."""
    headers = sign_in(client, OWNER_PHONE)
    client.patch(
        "/api/me",
        headers=headers,
        json={"is_displaced": False, "pre_displacement_place": PLACE, "show_displacement": True},
    )
    shop = _approved_shop(client, db, headers, category, location, name=ar("business.manakish"))
    for payload in _public_payloads(client, shop["slug"]):
        assert payload["displaced_from"] is None


def test_the_filter_finds_only_owners_who_chose_to_be_shown(
    client: TestClient,
    db: Session,
    displaced_owner: dict[str, str],
    category: Category,
    location: Location,
) -> None:
    shown = _approved_shop(
        client, db, displaced_owner, category, location, name=ar("business.manakish")
    )
    client.patch("/api/me", headers=displaced_owner, json={"show_displacement": True})

    # Displaced too, but has not chosen to say so: the filter must not reveal
    # by leaving them out... nor by including them.
    other = sign_in(client, OTHER_PHONE)
    client.patch(
        "/api/me", headers=other, json={"is_displaced": True, "pre_displacement_place": PLACE}
    )
    _approved_shop(client, db, other, category, location, name=ar("business.sweets_shop"))

    shops = client.get("/api/businesses", params={"displaced": "true"}).json()["items"]
    assert [b["slug"] for b in shops] == [shown["slug"]]

    products = client.get("/api/items", params={"displaced": "true"}).json()["items"]
    assert [p["business"]["slug"] for p in products] == [shown["slug"]]

    assert len(client.get("/api/businesses").json()["items"]) == 2


def test_shown_on_a_service_profile_and_filtered_the_same_way(
    client: TestClient,
    db: Session,
    displaced_owner: dict[str, str],
    location: Location,
) -> None:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()
    created = client.post(
        "/api/talent",
        headers=displaced_owner,
        json={
            "display_name": ar("business.manakish"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    profile = db.get(TalentProfile, created.json()["id"])
    assert profile is not None
    profile.status = BusinessStatus.APPROVED
    db.commit()
    slug = created.json()["slug"]

    assert client.get(f"/api/talent/{slug}").json()["displaced_from"] is None
    assert client.get("/api/talent", params={"displaced": "true"}).json()["items"] == []

    client.patch("/api/me", headers=displaced_owner, json={"show_displacement": True})
    assert client.get(f"/api/talent/{slug}").json()["displaced_from"] == PLACE
    listed = client.get("/api/talent", params={"displaced": "true"}).json()["items"]
    assert [p["slug"] for p in listed] == [slug]
    assert listed[0]["displaced_from"] == PLACE
