"""The candidate directory (the owners' ticket of 31 Oct 2026).

What is pinned here is what would quietly betray a candidate or an employer:

- a hidden photo reaches no public payload, search result or sitemap;
- a CV downloads only when it exists, the person allows it, and the profile
  is an approved job seeker -- and never through any other route;
- a job seeker's bio refuses contact details, and their name must be a name;
- an employer's request reaches the staff log, never a public read, and only
  for a job seeker;
- the new filters narrow the public directory and never widen it past
  APPROVED.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import (
    BusinessStatus,
    EducationLevel,
    TalentAvailability,
    TalentKind,
    TalentWorkType,
    VerificationDocumentKind,
)
from app.models.talent import EmployerRequest, TalentProfile, TalentWorkTypeRow
from app.models.taxonomy import Location
from app.models.verification import OwnerVerificationDocument
from tests.conftest import admin_headers, make_owner, sign_in

PHOTO = "/media/talent/photo-abc.jpg"


def _candidate(
    db: Session,
    location: Location,
    phone: str,
    *,
    name: str = "Rima Haddad",
    status: BusinessStatus = BusinessStatus.APPROVED,
    kind: TalentKind = TalentKind.JOB_SEEKER,
    **fields: object,
) -> TalentProfile:
    owner = make_owner(phone)
    profile = TalentProfile(
        owner_id=owner.id,
        display_name=name,
        slug=f"c-{phone}",
        kind=kind,
        location_id=location.id,
        status=status,
        search_text=name.lower(),
        **fields,
    )
    db.add(profile)
    db.commit()
    return profile


def _attach(db: Session, profile: TalentProfile, kind: VerificationDocumentKind) -> None:
    db.add(
        OwnerVerificationDocument(
            user_id=profile.owner_id,
            kind=kind,
            storage_key=f"verification/{profile.slug}-{kind.value}",
            content_type="application/pdf",
            original_filename="cv.pdf",
            size_bytes=10,
        )
    )
    db.commit()


# --- The hidden photo -------------------------------------------------------


def test_a_hidden_photo_is_in_no_public_payload(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970001", photo_url=PHOTO, photo_hidden=True)

    listing = client.get("/api/talent", params={"kind": "JOB_SEEKER"}).json()["items"][0]
    detail = client.get("/api/talent/c-03970001").json()
    assert listing["photo_url"] is None and listing["photo_thumb_url"] is None
    assert detail["photo_url"] is None
    assert PHOTO not in client.get("/api/talent/c-03970001").text
    assert PHOTO not in client.get("/sitemap.xml").text


def test_the_owner_still_sees_their_hidden_photo(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970002", photo_url=PHOTO, photo_hidden=True)
    own = client.get("/api/my/talent", headers=sign_in(client, "03970002")).json()
    assert own["photo_url"] == PHOTO and own["photo_hidden"] is True


# --- The CV -----------------------------------------------------------------


def test_the_cv_is_offered_only_when_allowed(
    client: TestClient, db: Session, location: Location
) -> None:
    allowed = _candidate(db, location, "03970010")
    kept = _candidate(db, location, "03970011", cv_public=False)
    none = _candidate(db, location, "03970012")
    pending = _candidate(db, location, "03970013", status=BusinessStatus.PENDING_REVIEW)
    service = _candidate(db, location, "03970014", kind=TalentKind.SERVICE)
    for profile in (allowed, kept, pending, service):
        _attach(db, profile, VerificationDocumentKind.CV)

    assert client.get(f"/api/talent/{allowed.slug}").json()["has_cv"] is True
    for profile in (kept, none, service):
        assert client.get(f"/api/talent/{profile.slug}").json()["has_cv"] is False
    # Refused alike, whatever the reason, so the answer says nothing.
    for profile in (kept, none, pending, service):
        assert client.get(f"/api/talent/{profile.slug}/cv").status_code == 404


def test_the_has_cv_filter_counts_only_offered_cvs(
    client: TestClient, db: Session, location: Location
) -> None:
    offered = _candidate(db, location, "03970020")
    kept = _candidate(db, location, "03970021", cv_public=False)
    _attach(db, offered, VerificationDocumentKind.CV)
    _attach(db, kept, VerificationDocumentKind.CV)
    items = client.get("/api/talent", params={"has_cv": True}).json()["items"]
    assert [item["slug"] for item in items] == [offered.slug]


# --- What a job seeker may type ---------------------------------------------


def test_a_job_seekers_bio_refuses_contact_details(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970030", status=BusinessStatus.DRAFT)
    headers = sign_in(client, "03970030")
    for bio in ("call me on 03 123 456", "write to me@example.com", "see www.example.com"):
        response = client.put("/api/my/talent", headers=headers, json={"bio": bio})
        assert response.status_code == 422, bio
        assert response.json()["error"]["code"] == "bio_has_contact"
    ok = client.put(
        "/api/my/talent", headers=headers, json={"bio": "Ten years in hotel reception."}
    )
    assert ok.status_code == 200


def test_a_job_seekers_name_must_be_a_name(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970031", status=BusinessStatus.DRAFT)
    headers = sign_in(client, "03970031")
    bad = client.put("/api/my/talent", headers=headers, json={"display_name": "nursing. home"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "name_not_person"
    good = client.put("/api/my/talent", headers=headers, json={"display_name": "Ali Raad"})
    assert good.status_code == 200


def test_a_service_profile_keeps_its_free_text(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970032", kind=TalentKind.SERVICE, status=BusinessStatus.DRAFT)
    response = client.put(
        "/api/my/talent",
        headers=sign_in(client, "03970032"),
        json={"display_name": "Nursing Home 24", "bio": "Call 03 123 456"},
    )
    assert response.status_code == 200


# --- Structured sections ----------------------------------------------------


def test_the_owner_saves_structured_sections(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970040", status=BusinessStatus.DRAFT)
    response = client.put(
        "/api/my/talent",
        headers=sign_in(client, "03970040"),
        json={
            "desired_title": "Hotel manager",
            "availability": "WITHIN_MONTH",
            "education_level": "UNIVERSITY",
            "work_types": ["FULL_TIME", "REMOTE", "FULL_TIME"],
            "work_area_ids": [str(location.id)],
            "team_message": "I prefer not to publish my face.",
            "experiences": [
                {"title": "Receptionist", "start_date": "2010-01-01", "end_date": "2014-01-01"},
                {"title": "Manager", "start_date": "2014-01-01", "is_current": True},
            ],
            "education": [{"degree": "BA", "field": "Hospitality", "graduation_year": 2009}],
            "courses": [{"name": "First aid", "year": 2020}],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["desired_title"] == "Hotel manager"
    assert body["availability"] == "WITHIN_MONTH"
    assert sorted(body["work_types"]) == ["FULL_TIME", "REMOTE"]
    assert [area["id"] for area in body["work_areas"]] == [str(location.id)]
    # Newest first, the current job on top.
    assert [e["title"] for e in body["experiences"]] == ["Manager", "Receptionist"]
    assert body["experiences"][0]["end_date"] is None
    assert body["years_experience"] == date.today().year - 2010 - (
        1 if (date.today().month, date.today().day) < (1, 1) else 0
    )
    assert body["education"][0]["field"] == "Hospitality"
    assert body["courses"][0]["name"] == "First aid"
    assert body["team_message"] == "I prefer not to publish my face."


def test_the_team_message_is_never_public(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03970041", team_message="private words")
    assert "private words" not in client.get("/api/talent/c-03970041").text
    assert "private words" not in client.get("/api/talent").text


# --- Filters ----------------------------------------------------------------


def test_the_candidate_filters_narrow_the_directory(
    client: TestClient, db: Session, location: Location
) -> None:
    senior = _candidate(
        db,
        location,
        "03970050",
        years_experience=12,
        education_level=EducationLevel.POSTGRADUATE,
        availability=TalentAvailability.NOW,
    )
    db.add(TalentWorkTypeRow(profile_id=senior.id, work_type=TalentWorkType.REMOTE))
    junior = _candidate(
        db,
        location,
        "03970051",
        years_experience=1,
        education_level=EducationLevel.SECONDARY_VOCATIONAL,
        availability=TalentAvailability.EMPLOYED_OPEN,
    )
    _candidate(db, location, "03970052", status=BusinessStatus.PENDING_REVIEW, years_experience=12)
    _attach(db, junior, VerificationDocumentKind.IDENTITY)

    def slugs(**params: object) -> list[str]:
        return [i["slug"] for i in client.get("/api/talent", params=params).json()["items"]]

    assert slugs(experience="10+") == [senior.slug]
    assert slugs(experience="0-1") == [junior.slug]
    assert slugs(education="POSTGRADUATE") == [senior.slug]
    assert slugs(work_type="REMOTE") == [senior.slug]
    assert slugs(available_now=True) == [senior.slug]
    assert slugs(verified=True) == [junior.slug]
    assert slugs(sort="best")[0] == senior.slug
    card = client.get("/api/talent", params={"verified": True}).json()["items"][0]
    assert card["id_verified"] is True


# --- Employer requests ------------------------------------------------------


def test_an_employer_request_reaches_the_staff_log_only(
    client: TestClient, db: Session, location: Location, admin: object
) -> None:
    profile = _candidate(db, location, "03970060", whatsapp="+96103970060")
    response = client.post(
        f"/api/talent/{profile.slug}/employer-requests",
        json={
            "employer_name": "Hotel Sour",
            "phone": "03970099",
            "company": "Hotel Sour",
            "job_title": "Front desk",
            "message": "Can you start next week?",
        },
    )
    assert response.status_code == 201, response.text
    assert "03970099" not in client.get(f"/api/talent/{profile.slug}").text

    headers = admin_headers(client)
    rows = client.get("/api/admin/employer-requests", headers=headers).json()
    assert len(rows) == 1 and rows[0]["candidate_slug"] == profile.slug
    assert rows[0]["candidate_whatsapp"] == "+96103970060"
    moved = client.post(
        f"/api/admin/employer-requests/{rows[0]['id']}/status",
        headers=headers,
        json={"status": "HIRED"},
    )
    assert moved.json()["status"] == "HIRED"
    assert client.get("/api/admin/employer-requests").status_code == 401


def test_an_employer_request_needs_an_approved_job_seeker(
    client: TestClient, db: Session, location: Location
) -> None:
    pending = _candidate(db, location, "03970061", status=BusinessStatus.PENDING_REVIEW)
    service = _candidate(db, location, "03970062", kind=TalentKind.SERVICE)
    body = {"employer_name": "Someone", "phone": "03970098"}
    for profile in (pending, service):
        response = client.post(f"/api/talent/{profile.slug}/employer-requests", json=body)
        assert response.status_code == 404
    assert db.query(EmployerRequest).count() == 0
