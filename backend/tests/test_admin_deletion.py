"""An administrator can permanently delete a listing, a product or a seller.

The owners asked for it (round 3): suspending hides, this removes -- the
row and every file it pointed at, as an owner deleting their own account
gets. An administrator account is never deletable this way.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessDocument, BusinessItem
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.storage.factory import get_storage
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

PHONE = "03991001"
OTHER_PHONE = "03991002"


def _pdf() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for tests\n"


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), (240, 240, 230)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _business(
    client: TestClient, headers: dict[str, str], category: Category, location: Location
) -> str:
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    business_id: str = created.json()["id"]
    return business_id


def _item(client: TestClient, headers: dict[str, str], business_id: str) -> str:
    created = client.post(
        f"/api/businesses/{business_id}/items",
        headers=headers,
        json={"title": ar("item.cheap"), "price": "5.00"},
    )
    assert created.status_code == 201, created.text
    item_id: str = created.json()["id"]
    return item_id


def test_an_admin_deletes_a_business_and_its_files_but_not_the_owner(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = sign_in(client, PHONE)
    business_id = _business(client, headers, category, location)
    uploaded = client.post(
        f"/api/businesses/{business_id}/documents",
        headers=headers,
        files={"file": ("register.pdf", _pdf(), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = db.query(BusinessDocument).filter_by(business_id=business_id).one()
    key = document.storage_key
    assert get_storage().exists(key)

    deleted = client.delete(f"/api/admin/businesses/{business_id}", headers=admin_headers(client))
    assert deleted.status_code == 200, deleted.text

    db.expire_all()
    assert db.get(Business, business_id) is None
    assert not get_storage().exists(key)
    # The owner is still there and can still sign in.
    assert client.get("/api/me", headers=headers).status_code == 200


def test_an_admin_deletes_one_product_and_only_from_its_own_listing(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = sign_in(client, PHONE)
    business_id = _business(client, headers, category, location)
    item_id = _item(client, headers, business_id)
    image = client.post(
        f"/api/businesses/{business_id}/items/{item_id}/image",
        headers=headers,
        files={"file": ("photo.jpg", _jpeg(), "image/jpeg")},
    )
    assert image.status_code == 200, image.text
    item = db.get(BusinessItem, item_id)
    assert item is not None
    key = item.image_storage_key
    assert key is not None and get_storage().exists(key)

    other_business = _business(client, sign_in(client, OTHER_PHONE), category, location)
    wrong = client.delete(
        f"/api/admin/businesses/{other_business}/items/{item_id}", headers=admin_headers(client)
    )
    assert wrong.status_code == 404

    deleted = client.delete(
        f"/api/admin/businesses/{business_id}/items/{item_id}", headers=admin_headers(client)
    )
    assert deleted.status_code == 200, deleted.text
    db.expire_all()
    assert db.get(BusinessItem, item_id) is None
    assert db.get(Business, business_id) is not None
    assert not get_storage().exists(key)


def test_an_admin_deletes_a_talent_profile(
    client: TestClient, db: Session, admin: User, location: Location
) -> None:
    skill = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(skill)
    db.commit()
    headers = sign_in(client, PHONE)
    created = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text

    deleted = client.delete(
        f"/api/admin/talent/{created.json()['id']}", headers=admin_headers(client)
    )
    assert deleted.status_code == 200, deleted.text
    db.expire_all()
    assert db.get(TalentProfile, created.json()["id"]) is None
    assert client.get("/api/me", headers=headers).status_code == 200


def test_an_admin_deletes_a_seller_account_with_everything_in_it(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = sign_in(client, PHONE)
    me = client.get("/api/me", headers=headers).json()
    business_id = _business(client, headers, category, location)

    deleted = client.delete(f"/api/admin/users/{me['id']}", headers=admin_headers(client))
    assert deleted.status_code == 200, deleted.text

    db.expire_all()
    assert db.get(User, me["id"]) is None
    assert db.get(Business, business_id) is None
    assert client.get("/api/me", headers=headers).status_code == 401


def test_an_administrator_account_is_never_deleted_this_way(
    client: TestClient, db: Session, admin: User
) -> None:
    response = client.delete(f"/api/admin/users/{admin.id}", headers=admin_headers(client))
    assert response.status_code == 403, response.text
    db.expire_all()
    assert db.get(User, admin.id) is not None


def test_deleting_is_admin_only(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, PHONE)
    business_id = _business(client, headers, category, location)
    me = client.get("/api/me", headers=headers).json()

    for path in (f"/api/admin/businesses/{business_id}", f"/api/admin/users/{me['id']}"):
        assert client.delete(path, headers=headers).status_code == 403
    db.expire_all()
    assert db.get(Business, business_id) is not None
