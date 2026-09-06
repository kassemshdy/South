"""The talent directory: one profile per person, moderated before it is public.

Two rules carry the weight here and are asserted directly rather than inferred:
a profile is invisible to an anonymous visitor until it is APPROVED (both via
search and via its own slug), and the owner routes resolve the profile from the
authenticated user, so there is no id a caller can substitute to reach someone
else's.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import BusinessStatus
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


@pytest.fixture
def skill(db: Session) -> TalentSkill:
    entity = TalentSkill(name_ar=ar("skill.design"), slug="design", sort_order=1)
    db.add(entity)
    db.commit()
    return entity


@pytest.fixture
def skill_other(db: Session) -> TalentSkill:
    """The seeded "Other" skill — real slug, since that's the sentinel the app
    looks for, not a NULL skill_id."""
    entity = TalentSkill(name_ar=ar("skill.other"), slug="other", sort_order=99)
    db.add(entity)
    db.commit()
    return entity


def _create_profile(
    client: TestClient,
    headers: dict[str, str],
    skill: TalentSkill,
    location: Location,
    *,
    display_name: str | None = None,
) -> dict:
    response = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": display_name or ar("talent.designer"),
            "headline": ar("talent.designer_headline"),
            "bio": ar("talent.designer_bio"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "whatsapp": "03950101",
            "years_experience": 7,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approve(client: TestClient, db: Session, admin: User, profile_id: str) -> None:
    """Push a profile all the way to APPROVED.

    Submission requires a photo, which needs a real upload; the tests that care
    about the *readiness* rules assert it explicitly, so everywhere else the
    status is set directly and only the moderation step goes through the API.
    """
    profile = db.get(TalentProfile, profile_id)
    assert profile is not None
    profile.status = BusinessStatus.PENDING_REVIEW
    db.commit()

    response = client.post(
        f"/api/admin/talent/{profile_id}/approve", headers=admin_headers(client)
    )
    assert response.status_code == 200, response.text


# --- Public visibility -----------------------------------------------------


def test_draft_profile_is_absent_from_public_search(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950101")
    _create_profile(client, headers, skill, location)

    assert client.get("/api/talent").json()["items"] == []


def test_draft_profile_404s_by_slug(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950102")
    profile = _create_profile(client, headers, skill, location)

    assert client.get(f"/api/talent/{profile['slug']}").status_code == 404


def test_approved_profile_is_public(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950103")
    profile = _create_profile(client, headers, skill, location)
    _approve(client, db, admin, profile["id"])

    listed = client.get("/api/talent").json()
    assert [item["slug"] for item in listed["items"]] == [profile["slug"]]

    detail = client.get(f"/api/talent/{profile['slug']}").json()
    assert detail["display_name"] == ar("talent.designer")
    assert detail["skill"]["slug"] == "design"
    # A public payload never carries moderation state.
    assert "status" not in detail
    assert "rejection_reason" not in detail


def test_suspending_removes_a_profile_from_the_public_directory(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950104")
    profile = _create_profile(client, headers, skill, location)
    _approve(client, db, admin, profile["id"])

    suspended = client.post(
        f"/api/admin/talent/{profile['id']}/suspend",
        headers=admin_headers(client),
        json={"reason": ar("moderation.suspend_reason")},
    )
    assert suspended.status_code == 200, suspended.text

    assert client.get("/api/talent").json()["items"] == []
    assert client.get(f"/api/talent/{profile['slug']}").status_code == 404


# --- Search ----------------------------------------------------------------


def test_search_matches_headline_and_filters_by_skill_and_location(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950105")
    profile = _create_profile(client, headers, skill, location)
    _approve(client, db, admin, profile["id"])

    assert client.get("/api/talent", params={"q": ar("search.talent_designer")}).json()[
        "meta"
    ]["total"] == 1
    assert client.get("/api/talent", params={"q": ar("search.talent_no_match")}).json()[
        "meta"
    ]["total"] == 0
    assert client.get("/api/talent", params={"skill": "design"}).json()["meta"]["total"] == 1
    assert client.get("/api/talent", params={"skill": "photography"}).json()["meta"][
        "total"
    ] == 0
    assert client.get("/api/talent", params={"location": location.slug}).json()["meta"][
        "total"
    ] == 1


def test_custom_skill_text_is_searchable_for_an_other_profile(
    client: TestClient, db: Session, admin: User, skill_other: TalentSkill, location: Location
) -> None:
    """An "Other" profile must be findable by what the person actually does,
    not by the literal word "Other" that every such profile shares."""
    headers = sign_in(client, "03950106")
    profile = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.photographer"),
            "headline": ar("talent.photographer_headline"),
            "skill_id": str(skill_other.id),
            "custom_skill_text": ar("talent.custom_skill_text"),
            "location_id": str(location.id),
            "whatsapp": "03950106",
        },
    ).json()
    _approve(client, db, admin, profile["id"])

    results = client.get("/api/talent", params={"q": ar("search.talent_garden")}).json()
    assert [item["slug"] for item in results["items"]] == [profile["slug"]]


# --- Ownership -------------------------------------------------------------


def test_one_profile_per_account(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950107")
    _create_profile(client, headers, skill, location)

    second = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.renamed"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "talent_profile_exists"


def test_owner_routes_only_ever_touch_the_callers_own_profile(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    owner = sign_in(client, "03950108")
    _create_profile(client, owner, skill, location)

    # A second account has no profile at all: the owner routes must 404 rather
    # than fall through to somebody else's.
    intruder = sign_in(client, "03950109")
    assert client.get("/api/my/talent", headers=intruder).status_code == 404
    assert (
        client.put(
            "/api/my/talent",
            headers=intruder,
            json={"display_name": ar("talent.stolen")},
        ).status_code
        == 404
    )
    assert client.delete("/api/my/talent", headers=intruder).status_code == 404

    # The original profile is untouched.
    assert client.get("/api/my/talent", headers=owner).json()["display_name"] == ar(
        "talent.designer"
    )


def test_owner_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/my/talent").status_code == 401
    assert client.post("/api/talent", json={"display_name": ar("talent.designer")}).status_code == 401


def test_admin_routes_reject_a_non_admin(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950110")
    profile = _create_profile(client, headers, skill, location)

    assert client.get("/api/admin/talent", headers=headers).status_code == 403
    assert (
        client.post(f"/api/admin/talent/{profile['id']}/approve", headers=headers).status_code
        == 403
    )


# --- Moderation ------------------------------------------------------------


def test_submission_lists_what_is_still_missing(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950111")
    client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    )

    readiness = client.get("/api/my/talent/readiness", headers=headers).json()
    assert set(readiness) == {
        "talent.field.headline",
        "talent.field.bio",
        "talent.field.photo",
        "talent.field.contact",
    }

    submitted = client.post("/api/my/talent/submit", headers=headers)
    assert submitted.status_code == 422
    assert submitted.json()["error"]["code"] == "incomplete_talent_profile"


def test_an_other_profile_must_name_its_own_skill(
    client: TestClient, skill_other: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950112")
    client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "headline": ar("talent.designer_headline"),
            "bio": ar("talent.designer_bio"),
            "skill_id": str(skill_other.id),
            "location_id": str(location.id),
            "whatsapp": "03950112",
        },
    )
    assert "talent.field.custom_skill" in client.get(
        "/api/my/talent/readiness", headers=headers
    ).json()


def test_rejection_reason_reaches_the_owner_and_clears_on_resubmit(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950113")
    profile = _create_profile(client, headers, skill, location)

    entity = db.get(TalentProfile, profile["id"])
    assert entity is not None
    entity.status = BusinessStatus.PENDING_REVIEW
    entity.photo_url = "https://example.invalid/photo.jpg"
    db.commit()

    rejected = client.post(
        f"/api/admin/talent/{profile['id']}/reject",
        headers=admin_headers(client),
        json={"reason": ar("moderation.reject_reason")},
    )
    assert rejected.status_code == 200, rejected.text

    owner_view = client.get("/api/my/talent", headers=headers).json()
    assert owner_view["status"] == "REJECTED"
    assert owner_view["rejection_reason"] == ar("moderation.reject_reason")

    resubmitted = client.post("/api/my/talent/submit", headers=headers)
    assert resubmitted.status_code == 200, resubmitted.text
    assert resubmitted.json()["status"] == "PENDING_REVIEW"
    assert resubmitted.json()["rejection_reason"] is None


def test_invalid_transition_is_rejected(
    client: TestClient, admin: User, skill: TalentSkill, location: Location
) -> None:
    """A DRAFT profile cannot be approved: it was never submitted."""
    headers = sign_in(client, "03950114")
    profile = _create_profile(client, headers, skill, location)

    response = client.post(
        f"/api/admin/talent/{profile['id']}/approve", headers=admin_headers(client)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status_transition"


def test_moderation_trail_is_recorded_for_the_admin(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950115")
    profile = _create_profile(client, headers, skill, location)
    _approve(client, db, admin, profile["id"])

    detail = client.get(
        f"/api/admin/talent/{profile['id']}", headers=admin_headers(client)
    ).json()
    assert [action["action"] for action in detail["moderation_actions"]] == ["APPROVE"]
    assert detail["owner_phone"] == "+9613950115"


# --- Taxonomy --------------------------------------------------------------


def test_public_skill_list_counts_only_approved_profiles(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    approved_owner = sign_in(client, "03950116")
    approved = _create_profile(client, approved_owner, skill, location)
    _approve(client, db, admin, approved["id"])

    draft_owner = sign_in(client, "03950117")
    _create_profile(
        client, draft_owner, skill, location, display_name=ar("talent.hidden")
    )

    skills = client.get("/api/talent-skills").json()
    design = next(entry for entry in skills if entry["slug"] == "design")
    assert design["talent_count"] == 1


def test_a_skill_in_use_cannot_be_deleted(
    client: TestClient, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03950118")
    _create_profile(client, headers, skill, location)

    response = client.delete(
        f"/api/admin/talent-skills/{skill.id}", headers=admin_headers(client)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "skill_in_use"


def test_admin_can_create_and_deactivate_a_skill(client: TestClient, db: Session, admin: User) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/talent-skills",
        headers=headers,
        json={"name_ar": ar("skill.design"), "slug": "design", "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    skill_id = created.json()["id"]

    # Deactivated skills disappear from the public list but keep their row.
    updated = client.put(
        f"/api/admin/talent-skills/{skill_id}", headers=headers, json={"is_active": False}
    )
    assert updated.status_code == 200, updated.text
    assert [entry["slug"] for entry in client.get("/api/talent-skills").json()] == []
    assert db.execute(select(TalentSkill).where(TalentSkill.slug == "design")).scalar_one()


# --- Slugs -----------------------------------------------------------------


def test_slug_is_stable_across_a_rename(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    """Renaming must not break a link somebody has already shared."""
    headers = sign_in(client, "03950119")
    profile = _create_profile(client, headers, skill, location)

    renamed = client.put(
        "/api/my/talent", headers=headers, json={"display_name": ar("talent.renamed")}
    ).json()
    assert renamed["display_name"] == ar("talent.renamed")
    assert renamed["slug"] == profile["slug"]
