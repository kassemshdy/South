"""Talent CV fields (ticket c7c5f3ae).

Everything here is published detail about the work -- education, training,
hobbies, employment preference -- never the account holder's identity, which
stays on ``users`` (see ``test_identity.py``). All fields are optional: a
profile can be as thin or as complete as the person wants.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
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


def _create_profile(client: TestClient, headers: dict[str, str], skill: TalentSkill, location: Location) -> dict:
    response = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.designer"),
            "headline": ar("talent.designer_headline"),
            "bio": ar("talent.designer_bio"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "highest_degree": ar("talent.degree"),
            "specialization": ar("talent.specialization"),
            "university": ar("talent.university"),
            "education_years": 4,
            "graduation_date": "2019-06-15",
            "study_focus": ar("talent.study_focus"),
            "professional_training": ar("talent.professional_training"),
            "hobbies": ar("talent.hobbies"),
            "employment_type": "PART_TIME",
            "remote_capable": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cv_fields_reach_the_owner(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03951001")
    profile = _create_profile(client, headers, skill, location)

    assert profile["education_years"] == 4
    assert profile["graduation_date"] == "2019-06-15"
    assert profile["study_focus"] == ar("talent.study_focus")
    assert profile["professional_training"] == ar("talent.professional_training")
    assert profile["hobbies"] == ar("talent.hobbies")
    assert profile["employment_type"] == "PART_TIME"
    assert profile["remote_capable"] is True


def test_cv_fields_are_published_and_optional(
    client: TestClient, db: Session, admin: User, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03951002")
    profile = _create_profile(client, headers, skill, location)

    record = db.get(TalentProfile, profile["id"])
    assert record is not None
    record.status = BusinessStatus.PENDING_REVIEW
    db.commit()
    approved = client.post(
        f"/api/admin/talent/{profile['id']}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text

    detail = client.get(f"/api/talent/{profile['slug']}").json()
    assert detail["study_focus"] == ar("talent.study_focus")
    assert detail["professional_training"] == ar("talent.professional_training")
    assert detail["hobbies"] == ar("talent.hobbies")
    assert detail["employment_type"] == "PART_TIME"
    assert detail["remote_capable"] is True


def test_fields_are_optional(client: TestClient, skill: TalentSkill, location: Location) -> None:
    headers = sign_in(client, "03951003")
    response = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.photographer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    )
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile["education_years"] is None
    assert profile["graduation_date"] is None
    assert profile["hobbies"] is None
    assert profile["employment_type"] is None
    assert profile["remote_capable"] is False


def test_an_unrecognised_employment_type_is_rejected(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03951004")
    response = client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.photographer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
            "employment_type": "FREELANCE",
        },
    )
    assert response.status_code == 422


def test_update_can_set_cv_fields_independently(
    client: TestClient, skill: TalentSkill, location: Location
) -> None:
    headers = sign_in(client, "03951005")
    client.post(
        "/api/talent",
        headers=headers,
        json={
            "display_name": ar("talent.photographer"),
            "skill_id": str(skill.id),
            "location_id": str(location.id),
        },
    )

    updated = client.put(
        "/api/my/talent",
        headers=headers,
        json={"remote_capable": True, "employment_type": "FULL_TIME"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["remote_capable"] is True
    assert body["employment_type"] == "FULL_TIME"
    # Untouched fields survive a partial update.
    assert body["display_name"] == ar("talent.photographer")
