"""The owners' services review (12 Nov 2026): a photo on each priced
service that survives edits, the services page's row of them, and an
administrator moving a shop that really offers a service into a services
profile."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar
from tests.test_admin_corrections import _listing
from tests.test_uploads_and_urls import make_image


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


def _profile(client: TestClient, skill: TalentSkill, location: Location, phone: str) -> dict[str, str]:
    headers = sign_in(client, phone)
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    return headers


def _offers(client: TestClient, headers: dict[str, str]) -> list[dict[str, object]]:
    return client.get("/api/my/talent", headers=headers).json()["service_offers"]


def test_an_offer_keeps_its_photo_through_an_edit(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = _profile(client, skill, location, "03950201")
    saved = client.put(
        "/api/my/talent",
        headers=headers,
        json={"service_offers": [{"title": ar("item.generic"), "price_from": "10.00"}]},
    )
    assert saved.status_code == 200, saved.text
    offer_id = saved.json()["service_offers"][0]["id"]

    photo = client.post(
        f"/api/my/talent/offers/{offer_id}/image",
        headers=headers,
        files={"file": ("p.jpg", make_image(), "image/jpeg")},
    )
    assert photo.status_code == 200, photo.text
    url = photo.json()["service_offers"][0]["image_url"]
    assert url

    # Edited with its id: same offer, photo kept, price changed.
    edited = client.put(
        "/api/my/talent",
        headers=headers,
        json={
            "service_offers": [
                {"id": offer_id, "title": ar("item.generic"), "price_from": "12.00"},
                {"title": ar("item.zaatar_local")},
            ]
        },
    )
    assert edited.status_code == 200, edited.text
    offers = _offers(client, headers)
    assert offers[0]["id"] == offer_id
    assert offers[0]["image_url"] == url
    assert offers[0]["price_from"] == "12.00"
    assert offers[1]["image_url"] is None

    # Left out, it goes, photo and all.
    client.put("/api/my/talent", headers=headers, json={"service_offers": []})
    assert _offers(client, headers) == []


def test_an_offer_photo_is_reached_only_through_its_own_profile(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    owner = _profile(client, skill, location, "03950202")
    offer_id = client.put(
        "/api/my/talent",
        headers=owner,
        json={"service_offers": [{"title": ar("item.generic")}]},
    ).json()["service_offers"][0]["id"]
    stranger = _profile(client, skill, location, "03950203")
    refused = client.post(
        f"/api/my/talent/offers/{offer_id}/image",
        headers=stranger,
        files={"file": ("p.jpg", make_image(), "image/jpeg")},
    )
    assert refused.status_code == 404


def test_the_services_row_shows_only_approved_offers_with_a_photo(
    client: TestClient, db: Session, skill: TalentSkill, location: Location
) -> None:
    headers = _profile(client, skill, location, "03950204")
    offers = client.put(
        "/api/my/talent",
        headers=headers,
        json={"service_offers": [{"title": ar("item.generic")}, {"title": ar("item.zaatar_local")}]},
    ).json()["service_offers"]
    client.post(
        f"/api/my/talent/offers/{offers[0]['id']}/image",
        headers=headers,
        files={"file": ("p.jpg", make_image(), "image/jpeg")},
    )
    # A draft profile's offers are not public.
    assert client.get("/api/talent/offers").json() == []

    profile = db.execute(select(TalentProfile)).scalar_one()
    profile.status = BusinessStatus.APPROVED
    db.commit()
    row = client.get("/api/talent/offers").json()
    assert [card["offer"]["id"] for card in row] == [offers[0]["id"]]
    assert row[0]["provider_slug"] == profile.slug


def test_an_administrator_moves_a_shop_into_services(
    client: TestClient,
    db: Session,
    admin: User,
    category: Category,
    location: Location,
    skill: TalentSkill,
) -> None:
    business_id, owner = _listing(client, category, location)
    post_item(
        client,
        f"/api/businesses/{business_id}/items",
        headers=owner,
        json={"title": ar("item.generic"), "price": "5.00", "currency": "USD"},
    )
    moved = client.post(
        f"/api/admin/businesses/{business_id}/convert-to-talent",
        headers=admin_headers(client),
        json={"skill_id": str(skill.id)},
    )
    assert moved.status_code == 200, moved.text

    db.expire_all()
    assert db.get(Business, business_id) is None
    profile = db.get(TalentProfile, moved.json()["profile_id"])
    assert profile is not None
    assert profile.display_name == ar("business.first")
    assert [offer.title for offer in profile.service_offers] == [ar("item.generic")]
    offer = profile.service_offers[0]
    assert offer.image_url is not None and str(offer.price_from) == "5.00"

    # The owner now lands on their services dashboard.
    mine = client.get("/api/my/talent", headers=owner)
    assert mine.status_code == 200, mine.text


def test_a_shop_whose_owner_already_has_a_profile_is_not_moved(
    client: TestClient,
    admin: User,
    category: Category,
    location: Location,
    skill: TalentSkill,
) -> None:
    business_id, owner = _listing(client, category, location)
    client.post(
        "/api/talent",
        headers=owner,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    refused = client.post(
        f"/api/admin/businesses/{business_id}/convert-to-talent",
        headers=admin_headers(client),
        json={"skill_id": str(skill.id)},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "owner_has_profile"
