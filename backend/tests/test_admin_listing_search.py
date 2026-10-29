"""The admin shop and service lists find a listing by phone number.

A number typed into the search on /admin/businesses used to find nothing:
the search only looked at names and descriptions (the owners' ticket, 29
Oct 2026). It now also matches the listing's own phone and WhatsApp and
the owner's sign-in number, however the number is typed.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.repositories.admin_search import phone_digits
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _found(client: TestClient, path: str, q: str) -> list[str]:
    response = client.get(path, headers=admin_headers(client), params={"q": q})
    assert response.status_code == 200, response.text
    return [row["id"] for row in response.json()["items"]]


def test_phone_digits_ignores_format_and_country_code() -> None:
    assert phone_digits("03 123 987") == "3123987"
    assert phone_digits("+961 3 123987") == "3123987"
    assert phone_digits("00961-3-123987") == "3123987"
    assert phone_digits("Shop 12") is None


def test_a_shop_is_found_by_its_owner_or_its_own_number(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03123987")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "71 555 444",
        },
    )
    assert created.status_code == 201, created.text
    shop = db.get(Business, created.json()["id"])
    assert shop is not None
    shop.status = BusinessStatus.APPROVED
    db.commit()
    sign_in(client, "70999888")  # another account, never matched

    for typed in ("03123987", "+961 3 123 987", "123987", "71555444"):
        assert _found(client, "/api/admin/businesses", typed) == [str(shop.id)], typed
    assert _found(client, "/api/admin/businesses", "76000000") == []


def test_a_service_profile_is_found_by_its_owner_number(
    client: TestClient, db: Session, admin: User, location: Location
) -> None:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()
    headers = sign_in(client, "03456789")
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("business.first"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    profile = db.get(TalentProfile, created.json()["id"])
    assert profile is not None

    assert _found(client, "/api/admin/talent", "03 456 789") == [str(profile.id)]
