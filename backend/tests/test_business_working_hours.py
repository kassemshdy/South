"""A business's opening hours: optional, owner-authored, and public.

Working hours describe the listing, not the account, so — like the address and
the producer detail — they are published on the business tier and carried back
through the owner's own view for editing. The field is deliberately free text:
one line as the owner would write it on their door.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar


def _create(client: TestClient, headers: dict[str, str], category: Category, location: Location, **extra):
    return client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            **extra,
        },
    )


def test_working_hours_are_published_on_the_public_profile(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    owner = sign_in(client, "03970101")
    created = _create(
        client, owner, category, location, working_hours=ar("business.working_hours")
    )
    assert created.status_code == 201, created.text
    business_id = created.json()["id"]

    business = db.get(Business, business_id)
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.commit()

    detail = client.get(f"/api/businesses/{business.slug}").json()
    assert detail["working_hours"] == ar("business.working_hours")


def test_working_hours_are_optional(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    owner = sign_in(client, "03970102")
    created = _create(client, owner, category, location)
    assert created.status_code == 201, created.text

    # Absent on the owner's own view means the field simply carries None, not
    # that the create was rejected for omitting it.
    assert created.json()["working_hours"] is None


def test_an_owner_can_set_working_hours_after_the_fact(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    owner = sign_in(client, "03970103")
    created = _create(client, owner, category, location)
    business_id = created.json()["id"]

    updated = client.put(
        f"/api/businesses/{business_id}",
        headers=owner,
        json={"working_hours": ar("business.working_hours")},
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["working_hours"] == ar("business.working_hours")


def test_blank_working_hours_clear_the_field(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    """A whitespace-only value is stripped to None rather than stored — the same
    rule the other optional text fields follow."""
    owner = sign_in(client, "03970104")
    created = _create(
        client, owner, category, location, working_hours=ar("business.working_hours")
    )
    business_id = created.json()["id"]

    cleared = client.put(
        f"/api/businesses/{business_id}", headers=owner, json={"working_hours": "   "}
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["working_hours"] is None


def test_over_long_working_hours_are_rejected(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    owner = sign_in(client, "03970105")
    created = _create(client, owner, category, location)
    business_id = created.json()["id"]

    too_long = client.put(
        f"/api/businesses/{business_id}",
        headers=owner,
        json={"working_hours": "x" * 201},
    )

    assert too_long.status_code == 422
