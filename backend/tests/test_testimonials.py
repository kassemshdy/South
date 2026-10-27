"""Testimonials: an administrator's approval publishes them (#48, round 3).

The rule these tests exist for is structural and the same one that governs
every other public payload here: **what is on the public schema is what is
published.** So the central assertion is negative -- a testimonial no
administrator has approved must be absent from the page a visitor receives.

The rest guard the decisions behind it: submission is anonymous and rate
limited; the administrator is the only route to visibility (the owners
removed the listing owner's approval in round 3); the owner reads only what
is published; every published rating counts. Service profiles take
testimonials and stars too.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus, TalentKind
from app.models.talent import TalentProfile, TalentSkill
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
            "latitude": 33.27,
            "longitude": 35.2,
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


def _approve(client: TestClient, testimonial_id: str) -> None:
    response = client.post(
        f"/api/admin/testimonials/{testimonial_id}/approve",
        headers=admin_headers(client),
    )
    assert response.status_code == 200, response.text


def _approve_all(client: TestClient) -> None:
    """Approve everything still awaiting review."""
    awaiting = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    ).json()
    for entry in awaiting:
        _approve(client, entry["id"])


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
    """The administrator's approval alone publishes it; the owner is not asked."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    _approve_all(client)

    profile = client.get(f"/api/businesses/{business.slug}").json()

    assert [entry["author_name"] for entry in profile["testimonials"]] == [
        ar("testimonial.author")
    ]
    # A visitor gets the text and nothing about moderation.
    assert set(profile["testimonials"][0]) == {
        "id", "author_name", "body", "rating", "created_at"
    }
    # The owner reads the same thing, with its state.
    theirs = client.get(
        f"/api/businesses/{business.id}/testimonials", headers=owner_headers
    ).json()
    assert [entry["status"] for entry in theirs] == ["APPROVED"]


def test_the_owner_can_neither_approve_nor_hide(
    client: TestClient,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """The owners' decision: what is published is the administrator's call
    alone, so the routes that let an owner decide are gone."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    entry = client.get("/api/admin/testimonials", headers=admin_headers(client)).json()[0]

    for action in ("approve", "hide"):
        response = client.post(
            f"/api/businesses/{business.id}/testimonials/{entry['id']}/{action}",
            headers=owner_headers,
        )
        assert response.status_code in (404, 405), response.text

    _approve(client, entry["id"])
    hidden = client.post(
        f"/api/businesses/{business.id}/testimonials/{entry['id']}/hide",
        headers=owner_headers,
    )
    assert hidden.status_code in (404, 405)
    assert len(client.get(f"/api/businesses/{business.slug}").json()["testimonials"]) == 1


def test_rejecting_a_published_one_takes_it_down_without_deleting_it(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
) -> None:
    """Kept rather than deleted, so the same text cannot quietly be
    resubmitted and approved again by accident."""
    _submit(
        client,
        business.slug,
        author=ar("testimonial.author"),
        body=ar("testimonial.body"),
    )
    _approve_all(client)
    entry = client.get("/api/admin/testimonials", headers=admin_headers(client)).json()[0]

    rejected = client.post(
        f"/api/admin/testimonials/{entry['id']}/reject", headers=admin_headers(client)
    )

    assert rejected.status_code == 200, rejected.text
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
    """Decided on the issue: no sign-in at all."""
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
    """A real delete, for abuse."""
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
    """The platform view: every submission in any state, alongside the
    listing it belongs to."""
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
    # Approve one, leaving the other waiting, so the survey carries both.
    first = client.get("/api/admin/testimonials", headers=admin_headers(client)).json()[-1]
    _approve(client, first["id"])

    survey = client.get("/api/admin/testimonials", headers=admin_headers(client))

    assert survey.status_code == 200, survey.text
    entries = survey.json()
    assert {entry["status"] for entry in entries} == {"PENDING_REVIEW", "APPROVED"}
    # Each carries the listing it is on, by public identity only.
    assert all(entry["business_slug"] == business.slug for entry in entries)
    assert all(entry["business_name"] == business.name for entry in entries)
    assert all(entry["talent_slug"] is None for entry in entries)
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
    approved = client.get("/api/admin/testimonials", headers=admin_headers(client)).json()[-1]
    _approve(client, approved["id"])

    pending_only = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    ).json()

    assert [entry["status"] for entry in pending_only] == ["PENDING_REVIEW"]


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


# --- The review ------------------------------------------------------------


def test_unreviewed_text_never_reaches_the_owner(
    client: TestClient, business: Business, owner_headers: dict[str, str]
) -> None:
    """Submitted text is absent from the owner's list until an administrator
    has approved it -- absent, not merely marked."""
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


def test_refused_text_reaches_neither_the_owner_nor_the_page(
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
    assert client.get(f"/api/businesses/{business.slug}").json()["testimonials"] == []
    # Still on record for the platform.
    assert db.get(Testimonial, uuid.UUID(entry["id"])) is not None


def test_the_review_is_admin_only(
    client: TestClient, business: Business, owner_headers: dict[str, str]
) -> None:
    """An owner cannot approve their own listing's testimonials: whoever
    benefits from the praise would be the one publishing it."""
    for action in ("approve", "reject"):
        response = client.post(
            f"/api/admin/testimonials/{uuid.uuid4()}/{action}", headers=owner_headers
        )
        assert response.status_code == 403


# --- Stars -------------------------------------------------------------------


def _publish(
    client: TestClient,
    path: str,
    *,
    rating: int | None,
    ip: str,
) -> str:
    """Submit and approve one testimonial on ``path`` (a listing's public
    testimonial route); return its id."""
    response = client.post(
        path,
        json={
            "author_name": ar("testimonial.author"),
            "body": ar("testimonial.body"),
            "rating": rating,
        },
        headers={"X-Forwarded-For": ip},
    )
    assert response.status_code == 201, response.text
    waiting = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    ).json()
    assert len(waiting) == 1
    _approve(client, waiting[0]["id"])
    testimonial_id: str = waiting[0]["id"]
    return testimonial_id


def _on(business: Business) -> str:
    return f"/api/businesses/{business.slug}/testimonials"


def test_stars_count_only_once_published_and_only_while_published(
    client: TestClient,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
) -> None:
    """Every published rating counts, and only published ones: the average
    is the average of what the page shows."""
    def summary() -> tuple[float | None, int]:
        page = client.get(f"/api/businesses/{business.slug}").json()
        return page["rating_average"], page["rating_count"]

    # Waiting on the platform: not counted.
    client.post(
        f"/api/businesses/{business.slug}/testimonials",
        json={"author_name": ar("testimonial.author"), "body": ar("testimonial.body"), "rating": 1},
        headers={"X-Forwarded-For": "10.0.1.1"},
    )
    assert summary() == (None, 0)
    reject = client.get(
        "/api/admin/testimonials", params={"status": "PENDING_REVIEW"}, headers=admin_headers(client)
    ).json()[0]
    client.post(f"/api/admin/testimonials/{reject['id']}/reject", headers=admin_headers(client))

    five = _publish(client, _on(business), rating=5, ip="10.0.1.2")
    _publish(client, _on(business), rating=4, ip="10.0.1.3")
    # Text without stars is published but leaves the average alone.
    _publish(client, _on(business), rating=None, ip="10.0.1.4")
    assert summary() == (4.5, 2)

    # Taken down by an administrator: no longer counted.
    taken_down = client.post(
        f"/api/admin/testimonials/{five}/reject", headers=admin_headers(client)
    )
    assert taken_down.status_code == 200, taken_down.text
    assert summary() == (4.0, 1)


def test_a_rating_outside_one_to_five_is_refused(client: TestClient, business: Business) -> None:
    for rating in (0, 6):
        response = client.post(
            f"/api/businesses/{business.slug}/testimonials",
            json={
                "author_name": ar("testimonial.author"),
                "body": ar("testimonial.body"),
                "rating": rating,
            },
        )
        assert response.status_code == 422, response.text


def test_sorting_by_rating_puts_rated_listings_first(
    client: TestClient,
    db: Session,
    business: Business,
    admin: User,
    owner_headers: dict[str, str],
    category: Category,
    location: Location,
) -> None:
    """The owners' order: rated listings, best first, then the unrated."""
    other = client.post(
        "/api/businesses",
        headers=sign_in(client, OTHER_PHONE),
        json={
            "name": ar("business.second_shop"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    ).json()
    record = db.get(Business, other["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()

    # The unrated one is newer, so it would lead an ordinary listing.
    assert client.get("/api/businesses").json()["items"][0]["name"] == ar("business.second_shop")

    _publish(client, _on(business), rating=3, ip="10.0.2.1")
    names = [row["name"] for row in client.get("/api/businesses?sort=rating").json()["items"]]
    assert names == [ar("business.sweets_shop"), ar("business.second_shop")]
    assert client.get("/api/items?sort=rating").status_code == 200


# --- Service profiles --------------------------------------------------------


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


def _service(
    client: TestClient,
    db: Session,
    skill: TalentSkill,
    location: Location,
    phone: str,
    *,
    name: str,
    kind: TalentKind = TalentKind.SERVICE,
) -> TalentProfile:
    created = client.post(
        "/api/talent",
        headers=sign_in(client, phone),
        json={
            "display_name": name,
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "kind": kind.value,
            "work_mode": "BOTH",
        },
    )
    assert created.status_code == 201, created.text
    profile = db.get(TalentProfile, uuid.UUID(created.json()["id"]))
    assert profile is not None
    profile.status = BusinessStatus.APPROVED
    db.commit()
    db.refresh(profile)
    return profile


def test_a_service_profile_takes_testimonials_and_stars(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    """The owners asked for testimonials and stars on services too, under the
    same rule: nothing shows until an administrator approves it."""
    profile = _service(client, db, skill, location, "03980011", name=ar("talent.designer"))
    path = f"/api/talent/{profile.slug}/testimonials"

    submitted = client.post(
        path,
        json={"author_name": ar("testimonial.author"), "body": ar("testimonial.body"), "rating": 4},
    )
    assert submitted.status_code == 201, submitted.text
    page = client.get(f"/api/talent/{profile.slug}").json()
    assert page["testimonials"] == []
    assert (page["rating_average"], page["rating_count"]) == (None, 0)

    entry = client.get("/api/admin/testimonials", headers=admin_headers(client)).json()[0]
    assert entry["talent_slug"] == profile.slug
    assert entry["business_slug"] is None
    _approve(client, entry["id"])

    page = client.get(f"/api/talent/{profile.slug}").json()
    assert [row["author_name"] for row in page["testimonials"]] == [ar("testimonial.author")]
    assert (page["rating_average"], page["rating_count"]) == (4.0, 1)

    # The owner reads what is published on their own profile.
    theirs = client.get("/api/my/talent/testimonials", headers=sign_in(client, "03980011"))
    assert theirs.status_code == 200, theirs.text
    assert [row["status"] for row in theirs.json()] == ["APPROVED"]


def test_a_job_application_takes_no_testimonial(
    client: TestClient, db: Session, skill: TalentSkill, location: Location
) -> None:
    """Someone asking for work is not a place for anonymous praise."""
    profile = _service(
        client,
        db,
        skill,
        location,
        "03980012",
        name=ar("talent.applicant"),
        kind=TalentKind.JOB_SEEKER,
    )
    response = client.post(
        f"/api/talent/{profile.slug}/testimonials",
        json={"author_name": ar("testimonial.author"), "body": ar("testimonial.body")},
    )
    assert response.status_code == 404


def test_services_sort_by_rating(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    """Rated profiles first, best first, then the unrated."""
    rated = _service(client, db, skill, location, "03980013", name=ar("talent.designer"))
    unrated = _service(client, db, skill, location, "03980014", name=ar("talent.applicant"))
    _publish(client, f"/api/talent/{rated.slug}/testimonials", rating=5, ip="10.0.3.1")

    slugs = [
        row["slug"]
        for row in client.get("/api/talent", params={"sort": "rating"}).json()["items"]
    ]
    assert slugs == [rated.slug, unrated.slug]


def test_deleting_a_service_profile_deletes_its_testimonials(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    profile = _service(client, db, skill, location, "03980015", name=ar("talent.designer"))
    _publish(client, f"/api/talent/{profile.slug}/testimonials", rating=3, ip="10.0.4.1")
    profile_id = profile.id

    deleted = client.delete("/api/my/talent", headers=sign_in(client, "03980015"))
    assert deleted.status_code == 200, deleted.text

    db.expire_all()
    remaining = db.execute(
        Testimonial.__table__.select().where(Testimonial.talent_profile_id == profile_id)
    ).all()
    assert remaining == []


def test_the_admin_dashboard_counts_testimonials_awaiting_review(
    client: TestClient, admin: User, business: Business
) -> None:
    """The dashboard's queue card: an approved testimonial leaves the count."""
    for index in range(2):
        response = _submit(
            client,
            business.slug,
            author=ar("testimonial.author"),
            body=ar("testimonial.body"),
            ip=f"10.0.0.{index + 1}",
        )
        assert response.status_code == 201, response.text

    def waiting() -> int:
        stats = client.get("/api/admin/stats", headers=admin_headers(client))
        return int(stats.json()["pending_testimonials"])

    assert waiting() == 2
    first = client.get(
        "/api/admin/testimonials",
        params={"status": "PENDING_REVIEW"},
        headers=admin_headers(client),
    ).json()[0]
    _approve(client, first["id"])
    assert waiting() == 1
