"""Staff follow-up of approved shops with nothing on sale (the owners'
request, 6 Nov 2026): mark one contacted with a note, filter by it, and keep
the note off every public payload."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite, _pending_business

LIST = "/api/admin/businesses?status=APPROVED&without_products=true"


def _approved_without_products(
    client: TestClient, db: Session, category: Category, location: Location
) -> str:
    business_id = _pending_business(client, db, category, location)
    entity = db.get(Business, business_id)
    assert entity is not None
    entity.status = BusinessStatus.APPROVED
    db.commit()
    return business_id


def test_a_shop_is_marked_contacted_with_a_note_and_filtered(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = admin_headers(client)
    business_id = _approved_without_products(client, db, category, location)
    note = ar("business.applicant_description")

    assert client.get(f"{LIST}&contacted=false", headers=headers).json()["meta"]["total"] == 1
    assert client.get(f"{LIST}&contacted=true", headers=headers).json()["meta"]["total"] == 0

    marked = client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=headers,
        json={"contacted": True, "note": note},
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["outreach_note"] == note
    contacted_at = marked.json()["outreach_contacted_at"]
    assert contacted_at

    assert client.get(f"{LIST}&contacted=false", headers=headers).json()["meta"]["total"] == 0
    contacted = client.get(f"{LIST}&contacted=true", headers=headers).json()
    assert contacted["meta"]["total"] == 1
    assert contacted["items"][0]["outreach_note"] == note

    # Editing the note keeps the date it was first contacted.
    edited = client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=headers,
        json={"contacted": True, "note": ar("business.first")},
    ).json()
    assert edited["outreach_contacted_at"] == contacted_at
    assert edited["outreach_note"] == ar("business.first")

    cleared = client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=headers,
        json={"contacted": False},
    ).json()
    assert cleared["outreach_contacted_at"] is None and cleared["outreach_note"] is None
    assert client.get(f"{LIST}&contacted=false", headers=headers).json()["meta"]["total"] == 1


def test_only_the_roles_that_talk_to_owners_mark_a_shop(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    manager = admin_headers(client)
    business_id = _approved_without_products(client, db, category, location)
    url = f"/api/admin/businesses/{business_id}/outreach"
    support = _invite(client, manager, "SUPPORT", "support-outreach@example.com")
    editor = _invite(client, manager, "EDITOR", "editor-outreach@example.com")
    assert client.put(url, headers=editor, json={"contacted": True}).status_code == 403
    assert client.put(url, headers=support, json={"contacted": True}).status_code == 200


def test_the_note_never_reaches_a_public_payload(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = admin_headers(client)
    business_id = _approved_without_products(client, db, category, location)
    client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=headers,
        json={"contacted": True, "note": ar("business.first")},
    )
    slug = db.get(Business, business_id).slug  # type: ignore[union-attr]
    public = client.get(f"/api/businesses/{slug}")
    assert public.status_code == 200
    assert "outreach_note" not in public.text
    assert "outreach_contacted_at" not in public.text


def test_a_contacted_shop_that_adds_a_product_moves_to_its_own_tab(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    """It no longer has nothing on sale, but staff still see it, apart (the
    owners' request, 6 Nov 2026)."""
    headers = admin_headers(client)
    business_id = _approved_without_products(client, db, category, location)
    client.put(
        f"/api/admin/businesses/{business_id}/outreach",
        headers=headers,
        json={"contacted": True, "note": None},
    )
    uploaded = "/api/admin/businesses?status=APPROVED&with_products=true&contacted=true"
    assert client.get(uploaded, headers=headers).json()["meta"]["total"] == 0

    db.add(
        BusinessItem(
            business_id=business_id,
            title=ar("item.generic"),
            slug="outreach-item",
            image_url="/media/x.jpg",
            is_available=True,
        )
    )
    db.commit()

    assert client.get(f"{LIST}&contacted=true", headers=headers).json()["meta"]["total"] == 0
    found = client.get(uploaded, headers=headers).json()
    assert found["meta"]["total"] == 1 and found["items"][0]["id"] == business_id
