"""The account holder's identity: stored once, published never.

Legal name, birth year, gender, marital status and the two civil-record
places describe the *person* behind an account. They live on ``users`` rather
than on any listing, because one account may hold a talent profile and
several businesses and a legal name cannot differ between them.

Publishing any of them means adding the field to a public schema, which is
the only thing standing between these columns and the open internet — so
that boundary is what these tests pin.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

IDENTITY_FIELDS = (
    "full_name",
    "birth_year",
    "gender",
    "marital_status",
    "registration_place",
    "residence_place",
    # A face is identity too, and is kept out of public payloads by the same
    # rule. It is not in IDENTITY_PAYLOAD below because it is not settable by
    # PATCH — it arrives as an upload — but every "must not appear publicly"
    # assertion should cover it.
    "photo_url",
)

IDENTITY_PAYLOAD = {
    "full_name": ar("identity.full_name"),
    "birth_year": 1994,
    "gender": "FEMALE",
    "marital_status": "SINGLE",
    "registration_place": ar("identity.registration_place"),
    "residence_place": ar("identity.residence_place"),
}


def test_account_stores_and_returns_its_own_identity(client: TestClient) -> None:
    headers = sign_in(client, "03960001")
    saved = client.patch("/api/me", headers=headers, json=IDENTITY_PAYLOAD)
    assert saved.status_code == 200, saved.text
    for field, value in IDENTITY_PAYLOAD.items():
        assert saved.json()[field] == value

    # Survives a fresh read, not just echoed back from the request body.
    reread = client.get("/api/me", headers=headers).json()
    for field, value in IDENTITY_PAYLOAD.items():
        assert reread[field] == value


def test_identity_fields_can_be_cleared_but_a_partial_patch_keeps_the_rest(
    client: TestClient,
) -> None:
    """One form section saving must not wipe another: only the keys sent are
    touched, and an explicit null clears rather than being ignored."""
    headers = sign_in(client, "03960002")
    client.patch("/api/me", headers=headers, json=IDENTITY_PAYLOAD)

    partial = client.patch(
        "/api/me", headers=headers, json={"residence_place": None}
    ).json()
    assert partial["residence_place"] is None
    assert partial["full_name"] == ar("identity.full_name")
    assert partial["birth_year"] == 1994


def test_an_impossible_birth_year_is_rejected(client: TestClient) -> None:
    headers = sign_in(client, "03960003")
    response = client.patch("/api/me", headers=headers, json={"birth_year": 12})
    assert response.status_code == 422, response.text


def test_identity_never_reaches_a_public_business_payload(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960004")
    client.patch("/api/me", headers=owner_headers, json=IDENTITY_PAYLOAD)
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03960004",
        },
    ).json()

    # A logo is required before review; set it directly rather than uploading.
    business = db.get(Business, created["id"])
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    submitted = client.post(
        f"/api/businesses/{created['id']}/submit", headers=owner_headers
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/api/admin/businesses/{created['id']}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text

    detail = client.get(f"/api/businesses/{created['slug']}").json()
    for field in IDENTITY_FIELDS:
        assert field not in detail, field
    assert "owner_identity" not in detail

    listed = client.get("/api/businesses").json()["items"][0]
    for field in IDENTITY_FIELDS:
        assert field not in listed, field

    # Nor is it findable — an owner's legal name is not a search term.
    found = client.get("/api/businesses", params={"q": ar("identity.full_name")})
    assert found.json()["meta"]["total"] == 0


def _photo_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 400), (120, 90, 70)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _upload_photo(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/me/photo",
        headers=headers,
        files={"file": ("face.jpg", _photo_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    url = response.json()["photo_url"]
    assert url
    return str(url)


def test_the_account_photo_is_returned_to_the_account_and_can_be_removed(
    client: TestClient,
) -> None:
    headers = sign_in(client, "03960010")
    assert client.get("/api/me", headers=headers).json()["photo_url"] is None

    url = _upload_photo(client, headers)
    assert client.get("/api/me", headers=headers).json()["photo_url"] == url

    removed = client.delete("/api/me/photo", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["photo_url"] is None


def test_the_account_photo_never_reaches_a_public_payload(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    """The reason this file exists, applied to a face rather than a name: an
    owner's photo is admin-only, and a public schema carrying it is the only
    way it could reach the open internet."""
    headers = sign_in(client, "03960011")
    _upload_photo(client, headers)
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03960011",
        },
    ).json()

    # A logo is required before review; set it directly rather than uploading.
    business = db.get(Business, created["id"])
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    assert (
        client.post(
            f"/api/businesses/{created['id']}/submit", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/admin/businesses/{created['id']}/approve",
            headers=admin_headers(client),
        ).status_code
        == 200
    )

    detail = client.get(f"/api/businesses/{created['slug']}").json()
    assert "photo_url" not in detail
    assert "owner_identity" not in detail
    assert "owner_photo_url" not in detail

    listed = client.get("/api/businesses").json()["items"][0]
    assert "photo_url" not in listed


def test_admin_review_payload_carries_the_owner_photo(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    """A reviewer checking that an application is a real person needs the face
    beside the name — and is the only reader who does."""
    owner_headers = sign_in(client, "03960012")
    photo_url = _upload_photo(client, owner_headers)
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    review = client.get(
        f"/api/admin/businesses/{created['id']}", headers=admin_headers(client)
    ).json()
    assert review["owner_identity"]["photo_url"] == photo_url


def test_admin_review_payload_carries_the_owner_identity(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960005")
    client.patch("/api/me", headers=owner_headers, json=IDENTITY_PAYLOAD)
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    review = client.get(
        f"/api/admin/businesses/{created['id']}", headers=admin_headers(client)
    )
    assert review.status_code == 200, review.text
    identity = review.json()["owner_identity"]
    assert identity is not None
    for field, value in IDENTITY_PAYLOAD.items():
        assert identity[field] == value


def test_owner_identity_is_null_when_nothing_was_provided(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    """An all-null block would read as "provided, empty"; a reviewer needs to
    see "not provided at all"."""
    owner_headers = sign_in(client, "03960006")
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    review = client.get(
        f"/api/admin/businesses/{created['id']}", headers=admin_headers(client)
    ).json()
    assert review["owner_identity"] is None


def test_one_account_shares_one_identity_across_its_listings(
    client: TestClient, admin: User, category: Category, location: Location
) -> None:
    """The whole reason identity sits on the account: two listings, one legal
    name, no second copy to fall out of step."""
    owner_headers = sign_in(client, "03960007")
    client.patch("/api/me", headers=owner_headers, json=IDENTITY_PAYLOAD)

    ids = []
    for name_key in ("business.manakish", "business.seo_name"):
        created = client.post(
            "/api/businesses",
            headers=owner_headers,
            json={
                "name": ar(name_key),
                "category_id": str(category.id),
                "location_id": str(location.id),
            },
        )
        assert created.status_code == 201, created.text
        ids.append(created.json()["id"])

    auth = admin_headers(client)
    names = {
        client.get(f"/api/admin/businesses/{business_id}", headers=auth).json()[
            "owner_identity"
        ]["full_name"]
        for business_id in ids
    }
    assert names == {ar("identity.full_name")}


# --- Producer detail: published, and searchable by what it makes ----------


def test_producer_detail_is_published_and_searchable(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    """A goods producer's registered name, founding date and what it makes are
    public — that is the point of listing them. Two of the three are also how
    a buyer finds the place."""
    owner_headers = sign_in(client, "03960008")
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03960008",
            "institution_name": ar("business.institution_name"),
            "founding_date": "1998-04-15",
            "production_nature": ar("business.production_nature"),
        },
    )
    assert created.status_code == 201, created.text
    business_id = created.json()["id"]

    business = db.get(Business, business_id)
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    client.post(f"/api/businesses/{business_id}/submit", headers=owner_headers)
    approved = client.post(
        f"/api/admin/businesses/{business_id}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text

    detail = client.get(f"/api/businesses/{approved.json()['slug']}").json()
    assert detail["institution_name"] == ar("business.institution_name")
    assert detail["founding_date"] == "1998-04-15"
    assert detail["production_nature"] == ar("business.production_nature")

    by_production = client.get(
        "/api/businesses", params={"q": ar("business.production_nature")[:12]}
    )
    assert by_production.json()["meta"]["total"] == 1

    by_institution = client.get(
        "/api/businesses", params={"q": ar("business.institution_name")[:12]}
    )
    assert by_institution.json()["meta"]["total"] == 1


def test_producer_detail_can_be_edited_after_creation(
    client: TestClient, category: Category, location: Location
) -> None:
    owner_headers = sign_in(client, "03960009")
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.manakish"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    updated = client.put(
        f"/api/businesses/{created['id']}",
        headers=owner_headers,
        json={
            "institution_name": ar("business.institution_name"),
            "production_nature": ar("business.production_nature"),
            "founding_date": "2020-01-31",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["institution_name"] == ar("business.institution_name")
    assert updated.json()["founding_date"] == "2020-01-31"
