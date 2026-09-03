"""Moderation workflow, audit trail, and public visibility invariants."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business, ModerationAction
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


@pytest.fixture
def complete_business(
    client: TestClient, category: Category, location: Location, db: Session
) -> tuple[str, dict[str, str]]:
    """A DRAFT business with everything required for submission."""
    headers = sign_in(client, "03800001")
    response = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03800001",
        },
    )
    business_id = response.json()["id"]

    # A logo is required before review; set it directly rather than uploading.
    business = db.get(Business, business_id)
    assert business is not None
    business.logo_url = "/media/test/logo.jpg"
    db.commit()

    return business_id, headers


def test_new_business_starts_as_draft(complete_business: tuple[str, dict[str, str]], client: TestClient) -> None:
    business_id, headers = complete_business
    assert client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()["status"] == "DRAFT"


def test_incomplete_business_cannot_be_submitted(
    client: TestClient, category: Category
) -> None:
    headers = sign_in(client, "03800002")
    business_id = client.post(
        "/api/businesses", headers=headers, json={"name": ar("business.incomplete")}
    ).json()["id"]

    response = client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "incomplete_business"
    assert len(response.json()["error"]["details"]["missing"]) > 0


def test_submit_moves_to_pending_review(
    client: TestClient, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    response = client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_REVIEW"
    assert response.json()["submitted_at"] is not None


def test_pending_business_is_invisible_to_the_public(
    client: TestClient, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    slug = client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()["slug"]
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    listing = client.get("/api/businesses", params={"q": ar("search.manakish")})
    profile = client.get(f"/api/businesses/{slug}")

    assert listing.json()["meta"]["total"] == 0
    assert profile.status_code == 404


def test_approval_publishes_the_business(
    client: TestClient, admin: User, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    slug = client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()["slug"]
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    approved = client.post(
        f"/api/admin/businesses/{business_id}/approve", headers=admin_headers(client)
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approved_at"] is not None
    assert approved.json()["owner_id"] is not None

    # Publicly searchable immediately after approval.
    assert client.get("/api/businesses", params={"q": ar("search.manakish")}).json()["meta"]["total"] == 1
    assert client.get(f"/api/businesses/{slug}").status_code == 200


def test_rejection_stores_the_reason_and_lets_the_owner_resubmit(
    client: TestClient, admin: User, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    rejected = client.post(
        f"/api/admin/businesses/{business_id}/reject",
        headers=admin_headers(client),
        json={"reason": ar("moderation.reject_reason")},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"

    owner_view = client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()
    assert owner_view["rejection_reason"] == ar("moderation.reject_reason")

    resubmitted = client.post(f"/api/businesses/{business_id}/submit", headers=headers)
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "PENDING_REVIEW"
    # The stale reason is cleared so the dashboard stops showing it.
    assert resubmitted.json()["rejection_reason"] is None


def test_rejection_requires_a_reason(
    client: TestClient, admin: User, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    response = client.post(
        f"/api/admin/businesses/{business_id}/reject",
        headers=admin_headers(client),
        json={"reason": ar("moderation.reject_reason_short")},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [("approve", 409), ("reject", 409), ("reactivate", 409)],
)
def test_illegal_transitions_are_refused(
    client: TestClient,
    admin: User,
    complete_business: tuple[str, dict[str, str]],
    action: str,
    expected_status: int,
) -> None:
    """A DRAFT business cannot be approved, rejected or reactivated."""
    business_id, _ = complete_business
    headers = admin_headers(client)

    response = client.post(
        f"/api/admin/businesses/{business_id}/{action}",
        headers=headers,
        json={"reason": ar("moderation.reject_reason_valid")},
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == "invalid_status_transition"


def test_suspend_hides_the_business_and_reactivate_restores_it(
    client: TestClient, admin: User, complete_business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = complete_business
    admin_auth = admin_headers(client)
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)
    client.post(f"/api/admin/businesses/{business_id}/approve", headers=admin_auth)

    client.post(
        f"/api/admin/businesses/{business_id}/suspend", headers=admin_auth, json={"reason": ar("moderation.suspend_reason")}
    )
    assert client.get("/api/businesses", params={"q": ar("search.manakish")}).json()["meta"]["total"] == 0

    client.post(f"/api/admin/businesses/{business_id}/reactivate", headers=admin_auth)
    assert client.get("/api/businesses", params={"q": ar("search.manakish")}).json()["meta"]["total"] == 1


def test_every_transition_is_recorded_in_the_audit_trail(
    client: TestClient, admin: User, complete_business: tuple[str, dict[str, str]], db: Session
) -> None:
    business_id, headers = complete_business
    admin_auth = admin_headers(client)

    client.post(f"/api/businesses/{business_id}/submit", headers=headers)
    client.post(f"/api/admin/businesses/{business_id}/approve", headers=admin_auth)
    client.post(f"/api/admin/businesses/{business_id}/suspend", headers=admin_auth, json={"reason": ar("moderation.suspend_reason")})
    client.post(f"/api/admin/businesses/{business_id}/reactivate", headers=admin_auth)

    actions = (
        db.query(ModerationAction)
        .filter(ModerationAction.business_id == business_id)
        .order_by(ModerationAction.created_at)
        .all()
    )

    assert [action.action.value for action in actions] == [
        "SUBMIT",
        "APPROVE",
        "SUSPEND",
        "REACTIVATE",
    ]
    assert actions[0].admin_id is None  # submitted by the owner
    assert actions[1].admin_id == admin.id
    assert actions[2].reason == ar("moderation.suspend_reason")


def test_public_endpoints_never_return_non_approved_businesses(
    client: TestClient, admin: User, category: Category, location: Location, db: Session
) -> None:
    """One assertion covering every status the public must not see."""
    headers = sign_in(client, "03800009")

    for index, status in enumerate(
        [
            BusinessStatus.DRAFT,
            BusinessStatus.PENDING_REVIEW,
            BusinessStatus.REJECTED,
            BusinessStatus.SUSPENDED,
        ]
    ):
        created = client.post(
            "/api/businesses",
            headers=headers,
            json={
                "name": f'{ar("business.hidden_prefix")} {index}',
                "short_description": ar("business.generic_short"),
                "category_id": str(category.id),
                "location_id": str(location.id),
            },
        ).json()
        business = db.get(Business, created["id"])
        assert business is not None
        business.status = status
        db.commit()

    listing = client.get("/api/businesses", params={"q": ar("search.hidden")})
    latest = client.get("/api/businesses/latest")
    sitemap = client.get("/sitemap.xml")

    assert listing.json()["meta"]["total"] == 0
    assert latest.json() == []
    assert ar("business.hidden_prefix") not in sitemap.text
