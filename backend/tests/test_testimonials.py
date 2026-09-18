"""Testimonials: a platform gate, then the owner's (#48).

The rule these tests exist for is structural and the same one that governs
every other public payload here: **what is on the public schema is what is
published.** So the central assertion is negative -- an unapproved
testimonial must be absent from the business profile a visitor receives.

The rest guard the decisions recorded on the issue: submission is anonymous
and rate limited, the owner is the only route to visibility, hiding does not
delete, and one owner can never reach another's testimonial.

Submitted text now waits on an administrator before the owner sees it at
all, so most of these go through ``_clear_all`` first. The two assertions
that gate is for are their own tests below: unreviewed text does not reach
the owner, and refused text never does.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus, TestimonialStatus
from app.models.taxonomy import Category, Location
from app.models.testimonial import Testimonial
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

OWNER_PHONE = "03980001"
OTHER_PHONE = "03980002"


@pytest.fixture
def owner_headers(client: TestClient) -> dict[str, str]:
    return sign_in(client, OWNER_PHONE)


@pytest.fixture
def business(
    client: TestClient,
    db: Session,
    owner_headers: dict[str, str],
    category: Category,
    location: Location,
) -> Business:
    created = client.post(
        "/api/businesses",
        headers=owner_headers,
        json={
            "name": ar("business.sweets_shop"),
            "short_description": ar("business.sweets_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    entity = db.get(Business, created.json()["id"])
    assert entity is not None
    entity.status = BusinessStatus.APPROVED
    db.commit()
    db.refresh(entity)
    return entity


def _submit(
    client: TestClient, slug: str, *, author: str, body: str, ip: str | None = None
):
    # get_client_ip honours X-Forwarded-For, which is what lets these tests
    # separate the per-address rule from the per-listing one.
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post(
        f"/api/businesses/{slug}/testimonials",
        json={"author_name": author, "body": body},
        headers=headers,
    )


def _clear(client: TestClient, testimonial_id: str) -> None:
    """Pass the platform gate, which every owner action now sits behind."""
    response = client.post(
        f"/api/admin/testimonials/{testimonial_id}/clear",
        headers=admin_headers(client),
    )
    assert response.status_code == 200, response.text


def _clear_all(client: TestClient) -> None:
    """Clear everything still awaiting review.

    Used by the tests that are about what happens *after* the platform gate,
    so they read as the owner flow they are testing rather than restating the
    gate at every call site.
    """
    awaiting = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    ).json()
    for entry in awaiting:
        _clear(client, entry["id"])


# --- The disclosure rule ---------------------------------------------------


def test_an_unapproved_testimonial_is_absent_from_the_public_profile(
    client: TestClient, db: Session, business: Business
) -> None:
    """The assertion this whole feature rests on.

    Submitted praise is invisible until the owner says otherwise. If this
    ever passes something through, the moderation model is decorative.
    """
    submitted = _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    assert submitted.status_code == 201, submitted.text

    profile = client.get(f"/api/businesses/{business.slug}").json()

    assert profile["testimonials"] == []


def test_an_approved_testimonial_appears_on_the_public_profile(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    _clear_all(client)
    pending = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()
    assert len(pending) == 1
    assert pending[0]["status"] == "PENDING_OWNER"

    approved = client.post(
        f"/api/businesses/{business.id}/testimonials/{pending[0]['id']}/approve",
        headers=owner_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    profile = client.get(f"/api/businesses/{business.slug}").json()

    assert [entry["author_name"] for entry in profile["testimonials"]] == [
        ar("testimonial.author")
    ]
    # A visitor gets the text and nothing about moderation.
    assert set(profile["testimonials"][0]) == {"id", "author_name", "body", "created_at"}


def test_hiding_removes_it_from_the_public_profile_without_deleting_it(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """Hidden rather than deleted, so the same text cannot quietly be
    resubmitted and re-approved, and an admin can still see what was
    published."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    _clear_all(client)
    entry = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()[0]
    client.post(
        f"/api/businesses/{business.id}/testimonials/{entry['id']}/approve",
        headers=owner_headers,
    )

    hidden = client.post(
        f"/api/businesses/{business.id}/testimonials/{entry['id']}/hide",
        headers=owner_headers,
    )

    assert hidden.status_code == 200, hidden.text
    assert client.get(f"/api/businesses/{business.slug}").json()["testimonials"] == []
    assert db.get(Testimonial, uuid.UUID(entry["id"])) is not None


def test_a_listing_a_visitor_cannot_see_accepts_no_testimonial(
    client: TestClient, db: Session, business: Business
) -> None:
    """Submission goes through the public lookup, so a draft or suspended
    listing is not a place to leave text."""
    business.status = BusinessStatus.SUSPENDED
    db.commit()

    response = _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )

    assert response.status_code == 404


# --- Anonymous, and therefore rate limited ---------------------------------


def test_submission_needs_no_account(client: TestClient, business: Business) -> None:
    """Decided on the issue: no sign-in and no OTP. Verifying the author
    would imply an independence owner-approved praise does not have."""
    response = _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )

    assert response.status_code == 201


def test_one_sender_is_rate_limited(client: TestClient, business: Business) -> None:
    """The per-address rule: stops one person spraying the directory.

    Five per hour, from the settings. Written as a loop to the limit rather
    than a magic 6th call, so a change to the setting fails here loudly
    instead of passing for the wrong reason.
    """
    limit = 5
    for index in range(limit):
        assert (
            _submit(
                client,
                business.slug,
                author=ar("testimonial.author"),
                body=f"{ar('testimonial.body')} {index}",
                ip="198.51.100.7",
            ).status_code
            == 201
        )

    blocked = _submit(
        client,
        business.slug,
        author=ar("testimonial.second_author"),
        body=ar("testimonial.second_body"),
        ip="198.51.100.7",
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["details"]["retry_after_seconds"] > 0


def test_one_listing_cannot_be_flooded_from_many_addresses(
    client: TestClient, business: Business
) -> None:
    """The per-listing rule, which is the one that protects the person who
    would otherwise have to read the flood.

    Each submission comes from a different address, so the per-address rule
    never binds -- if the two rules were the same rule, this test could not
    distinguish them and would stop at five.
    """
    limit = 20
    for index in range(limit):
        assert (
            _submit(
                client,
                business.slug,
                author=ar("testimonial.author"),
                body=f"{ar('testimonial.body')} {index}",
                ip=f"203.0.113.{index}",
            ).status_code
            == 201
        ), f"submission {index} from a fresh address should not be limited"

    blocked = _submit(
        client,
        business.slug,
        author=ar("testimonial.second_author"),
        body=ar("testimonial.second_body"),
        ip="203.0.113.200",
    )

    assert blocked.status_code == 429


@pytest.mark.parametrize(
    ("author", "body"),
    [
        ("", "a valid body that is long enough"),
        ("A", "a valid body that is long enough"),
        ("A valid name", "too short"),
        ("A valid name", ""),
    ],
)
def test_a_submission_must_be_substantial(
    client: TestClient, business: Business, author: str, body: str
) -> None:
    """Length caps are the other half of accepting unauthenticated text."""
    assert _submit(client, business.slug, author=author, body=body).status_code == 422


# --- Scoping ---------------------------------------------------------------


def test_one_owner_cannot_reach_another_listings_testimonial(
    client: TestClient,
    db: Session,
    business: Business,
    category: Category,
    location: Location,
) -> None:
    """Scoped by business id inside the repository, so an id swapped into the
    URL of a listing you *do* own still reaches nothing."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    target = db.execute(
        Testimonial.__table__.select().where(
            Testimonial.business_id == business.id
        )
    ).first()
    assert target is not None

    stranger = sign_in(client, OTHER_PHONE)
    theirs = client.post(
        "/api/businesses",
        headers=stranger,
        json={
            "name": ar("business.other_shop"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()

    response = client.post(
        f"/api/businesses/{theirs['id']}/testimonials/{target.id}/approve",
        headers=stranger,
    )

    assert response.status_code == 404
    assert db.get(Testimonial, target.id).status is TestimonialStatus.PENDING_REVIEW


def test_listing_testimonials_requires_owning_the_listing(
    client: TestClient, business: Business
) -> None:
    stranger = sign_in(client, OTHER_PHONE)

    response = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=stranger
    )

    assert response.status_code == 404


# --- Admin -----------------------------------------------------------------


def test_an_admin_can_remove_one_outright(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """The owner controls display; the platform keeps the last word on abuse."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    entry = client.get(
        "/api/admin/testimonials", headers=admin_headers(client)
    ).json()[0]

    removed = client.delete(
        f"/api/admin/testimonials/{entry['id']}", headers=admin_headers(client)
    )

    assert removed.status_code == 200, removed.text
    assert db.get(Testimonial, uuid.UUID(entry["id"])) is None


def test_an_admin_can_survey_every_testimonial_in_any_state(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """The point of the platform view: a submission the owner has not acted on
    is still visible here, alongside the listing it belongs to. The owner sees
    only their own; the admin sees the whole directory."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
        ip="198.51.100.1",
    )
    _submit(
        client,
        business.slug,
        author=ar("testimonial.second_author"),
        body=ar("testimonial.second_body"),
        ip="198.51.100.2",
    )
    _clear_all(client)
    # Approve one, leaving the other with the owner, so the survey carries both.
    first = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()[-1]
    client.post(
        f"/api/businesses/{business.id}/testimonials/{first['id']}/approve",
        headers=owner_headers,
    )

    survey = client.get("/api/admin/testimonials", headers=admin_headers(client))

    assert survey.status_code == 200, survey.text
    entries = survey.json()
    assert {entry["status"] for entry in entries} == {"PENDING_OWNER", "APPROVED"}
    # Each carries the listing it is on, by public identity only.
    assert all(entry["business_slug"] == business.slug for entry in entries)
    assert all(entry["business_name"] == business.name for entry in entries)
    # Never the owner's identity: the platform view is public-shaped.
    assert all("owner_identity" not in entry for entry in entries)


def test_the_admin_survey_filters_by_status(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
        ip="198.51.100.3",
    )
    _submit(
        client,
        business.slug,
        author=ar("testimonial.second_author"),
        body=ar("testimonial.second_body"),
        ip="198.51.100.4",
    )
    _clear_all(client)
    approved = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()[-1]
    client.post(
        f"/api/businesses/{business.id}/testimonials/{approved['id']}/approve",
        headers=owner_headers,
    )

    pending_only = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_OWNER"},
        headers=admin_headers(client),
    ).json()

    assert [entry["status"] for entry in pending_only] == ["PENDING_OWNER"]


def test_the_admin_survey_is_admin_only(
    client: TestClient, business: Business, owner_headers: dict[str, str]
) -> None:
    response = client.get("/api/admin/testimonials", headers=owner_headers)

    assert response.status_code == 403


def test_removal_is_admin_only(
    client: TestClient, business: Business, admin: User, owner_headers: dict[str, str]
) -> None:
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    entry = client.get(
        "/api/admin/testimonials", headers=admin_headers(client)
    ).json()[0]

    response = client.delete(
        f"/api/admin/testimonials/{entry['id']}", headers=owner_headers
    )

    assert response.status_code == 403


# --- Deleting the listing --------------------------------------------------


def test_deleting_the_business_deletes_its_testimonials(
    client: TestClient,
    db: Session,
    business: Business,
    owner_headers: dict[str, str],
) -> None:
    """Unlike the view counter, this one has a real foreign key, so the
    cascade is the database's job -- asserted rather than assumed."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    business_id = business.id

    client.delete(f"/api/businesses/{business_id}", headers=owner_headers)

    remaining = db.execute(
        Testimonial.__table__.select().where(Testimonial.business_id == business_id)
    ).all()
    assert remaining == []


# --- The platform gate -----------------------------------------------------


def test_unreviewed_text_never_reaches_the_owner(
    client: TestClient, business: Business, owner_headers: dict[str, str]
) -> None:
    """The reason the platform gate exists.

    An owner asked to hide abuse has already read it. So submitted text is
    absent from the owner's list until an administrator has passed it —
    absent, not merely marked.
    """
    submitted = _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    assert submitted.status_code == 201

    theirs = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    )

    assert theirs.status_code == 200
    assert theirs.json() == []


def test_clearing_hands_it_to_the_owner_without_publishing_it(
    client: TestClient, business: Business, admin: User, owner_headers: dict[str, str]
) -> None:
    """Clearing is not publishing: the owner still decides.

    This is what keeps a testimonial selected praise rather than a review —
    an administrator passing it does not put it on the page.
    """
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    _clear_all(client)

    theirs = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()

    assert [entry["status"] for entry in theirs] == ["PENDING_OWNER"]
    assert client.get(f"/api/businesses/{business.slug}").json()["testimonials"] == []


def test_refused_text_reaches_neither_the_owner_nor_the_page(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """Rejected is a dead end, and not reachable by guessing the id.

    Kept in the table rather than deleted, so the same text cannot be
    resubmitted and cleared by accident — but the owner can neither see it
    nor act on it, which is the whole point of refusing it for them.
    """
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    entry = client.get(
        "/api/admin/testimonials", headers=admin_headers(client)
    ).json()[0]

    refused = client.post(
        f"/api/admin/testimonials/{entry['id']}/reject", headers=admin_headers(client)
    )

    assert refused.status_code == 200, refused.text
    assert refused.json()["status"] == "REJECTED"
    assert (
        client.get(
            f"/api/businesses/{business.id}/testimonials", headers=owner_headers
        ).json()
        == []
    )
    # Not reachable by id either: absent from the list is absent by id.
    reached = client.post(
        f"/api/businesses/{business.id}/testimonials/{entry['id']}/approve",
        headers=owner_headers,
    )
    assert reached.status_code == 404
    assert client.get(f"/api/businesses/{business.slug}").json()["testimonials"] == []
    # Still on record for the platform.
    assert db.get(Testimonial, uuid.UUID(entry["id"])) is not None


def test_the_platform_gate_is_admin_only(
    client: TestClient, business: Business, owner_headers: dict[str, str]
) -> None:
    """An owner cannot clear their own listing's testimonials.

    Otherwise the gate is decorative: whoever benefits from the praise would
    be the one deciding it is not abuse.
    """
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )

    cleared = client.post(
        f"/api/admin/testimonials/{uuid.uuid4()}/clear", headers=owner_headers
    )
    rejected = client.post(
        f"/api/admin/testimonials/{uuid.uuid4()}/reject", headers=owner_headers
    )

    assert cleared.status_code == 403
    assert rejected.status_code == 403
