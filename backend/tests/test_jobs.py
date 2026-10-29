"""Job openings (29 Oct 2026): written by administrators, applied
to anonymously with a CV; applications are read by staff, the CV by
reviewers and the manager only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import PRIVATE_MEDIA_FOLDERS
from app.models.job import JobApplication, JobOpening
from app.models.user import User
from app.services import telegram_archive
from app.services.job_applications import EMPLOYER_ID_FOLDER, FOLDER
from app.storage.factory import get_storage
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_permissions import _invite
from tests.test_product_profile import make_image

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _create(
    client: TestClient, headers: dict[str, str], *, publish: bool = True, **extra: object
) -> dict:
    body = {
        "title": ar("business.first"),
        "description": ar("business.applicant_description"),
        **extra,
    }
    created = client.post("/api/admin/job-openings", headers=headers, json=body)
    assert created.status_code == 201, created.text
    job = created.json()
    if publish:
        published = client.post(f"/api/admin/job-openings/{job['id']}/publish", headers=headers)
        assert published.status_code == 200, published.text
    return job


def _apply(client: TestClient, slug: str, data: bytes = PDF, **fields: str):  # type: ignore[no-untyped-def]
    form = {
        "full_name": ar("order.customer"),
        "email": "applicant@example.com",
        "phone_number": "03123456",
        **fields,
    }
    return client.post(
        f"/api/job-openings/{slug}/apply",
        data=form,
        files={"cv": ("cv.pdf", data, "application/pdf")},
    )


def test_a_draft_or_closed_opening_reaches_nobody(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    draft = _create(client, headers, publish=False)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    closed = _create(client, headers, slug="closed", deadline=yesterday)
    open_job = _create(client, headers, slug="open")

    assert [j["slug"] for j in client.get("/api/job-openings").json()] == [open_job["slug"]]
    for job in (draft, closed):
        assert client.get(f"/api/job-openings/{job['slug']}").status_code == 404
        assert _apply(client, job["slug"]).status_code == 404
    assert "/vacancies/open<" in client.get("/sitemap.xml").text
    assert "/vacancies/closed<" not in client.get("/sitemap.xml").text


def test_an_application_with_its_cv_is_kept_for_staff(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    job = _create(client, headers)

    sent = _apply(client, job["slug"])
    assert sent.status_code == 201, sent.text
    public = client.get(f"/api/job-openings/{job['slug']}").text
    assert "applicant@example.com" not in public and "application_count" not in public

    [row] = client.get(f"/api/admin/job-openings/{job['id']}/applications", headers=headers).json()
    assert row["email"] == "applicant@example.com" and row["phone_number"].endswith("3123456")
    stored = db.get(JobApplication, row["id"])
    assert stored is not None and stored.storage_key.startswith(f"{FOLDER}/")
    assert client.get(f"/media/{stored.storage_key}").status_code == 404, "never public"

    cv_url = f"/api/admin/job-openings/{job['id']}/applications/{row['id']}/cv"
    downloaded = client.get(cv_url, headers=headers)
    assert downloaded.status_code == 200 and downloaded.content == PDF
    support = _invite(client, headers, "SUPPORT", "support-jobs@example.com")
    assert client.get(cv_url, headers=support).status_code == 403, "CVs: reviewers and manager"
    assert client.get(f"/api/admin/job-openings/{job['id']}/applications", headers=support).status_code == 200


def test_a_file_that_is_not_a_document_is_refused_before_anything_is_stored(
    client: TestClient, db: Session, admin: User
) -> None:
    job = _create(client, admin_headers(client))
    refused = _apply(client, job["slug"], data=b"MZ\x90\x00 not a cv")
    assert refused.status_code == 415
    assert _apply(client, job["slug"], email="not-an-email").status_code == 422
    assert db.query(JobApplication).count() == 0


def test_deleting_an_opening_removes_its_applications(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    job = _create(client, headers)
    assert _apply(client, job["slug"]).status_code == 201
    assert client.delete(f"/api/admin/job-openings/{job['id']}", headers=headers).status_code == 200
    assert db.query(JobApplication).count() == 0


def test_content_editors_write_openings_and_support_cannot(
    client: TestClient, admin: User
) -> None:
    manager = admin_headers(client)
    editor = _invite(client, manager, "EDITOR", "editor-jobs@example.com")
    support = _invite(client, manager, "SUPPORT", "support-jobs2@example.com")
    body = {"title": ar("business.first"), "description": ar("business.applicant_description")}
    assert client.post("/api/admin/job-openings", headers=editor, json=body).status_code == 201
    assert client.post("/api/admin/job-openings", headers=support, json=body).status_code == 403


def test_applications_are_archived_and_cvs_are_private() -> None:
    assert {"job_applications", "job_openings"} <= telegram_archive.ARCHIVED_TABLES
    assert {FOLDER, EMPLOYER_ID_FOLDER} <= PRIVATE_MEDIA_FOLDERS


def _offer(client: TestClient, data: bytes = PDF, **fields: str):  # type: ignore[no-untyped-def]
    form = {
        "submitter_name": ar("order.customer"),
        "phone_number": "70111222",
        "employer_name": ar("business.first"),
        "work_place": ar("business.second"),
        "work_mode": "BOTH",
        "title": ar("business.generic_short"),
        "description": ar("business.applicant_description"),
        **fields,
    }
    return client.post(
        "/api/job-openings/offer",
        data=form,
        files={"id_document": ("id.pdf", data, "application/pdf")},
    )


def test_an_employer_offer_arrives_as_a_draft_with_who_sent_it(
    client: TestClient, db: Session, admin: User
) -> None:
    sent = _offer(client)
    assert sent.status_code == 201, sent.text
    assert client.get("/api/job-openings").json() == [], "nothing is published unchecked"

    headers = admin_headers(client)
    [job] = client.get("/api/admin/job-openings", headers=headers).json()
    assert job["is_published"] is False and job["work_mode"] == "BOTH"
    assert job["submitter_name"] == ar("order.customer")
    assert job["submitter_phone"].endswith("70111222") and job["has_id_document"] is True

    stored = db.get(JobOpening, job["id"])
    assert stored is not None and stored.id_document_storage_key is not None
    assert stored.id_document_storage_key.startswith(f"{EMPLOYER_ID_FOLDER}/")
    assert client.get(f"/media/{stored.id_document_storage_key}").status_code == 404

    id_url = f"/api/admin/job-openings/{job['id']}/id-document"
    assert client.get(id_url, headers=headers).content == PDF
    support = _invite(client, headers, "SUPPORT", "support-offer@example.com")
    assert client.get(id_url, headers=support).status_code == 403

    # Published, the visitor reads the job and never who offered it.
    client.post(f"/api/admin/job-openings/{job['id']}/publish", headers=headers)
    public = client.get(f"/api/job-openings/{job['slug']}")
    assert public.status_code == 200
    assert "submitter" not in public.text and "70111222" not in public.text
    assert "id_document" not in public.text


def test_an_offer_without_a_real_document_is_refused_and_leaves_nothing(
    client: TestClient, db: Session
) -> None:
    assert _offer(client, data=b"not a document").status_code == 415
    assert _offer(client, work_mode="SOMETIMES").status_code == 422
    assert db.query(JobOpening).count() == 0


def _cover_key(db: Session, job_id: str) -> str | None:
    db.expire_all()
    job = db.get(JobOpening, job_id)
    assert job is not None
    return job.cover_storage_key


def test_a_thumbnail_is_shown_replaced_and_removed_with_its_file(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    job = _create(client, headers)
    url = f"/api/admin/job-openings/{job['id']}/image"

    def photo() -> dict[str, tuple[str, bytes, str]]:
        return {"file": ("thumb.jpg", make_image((600, 400)), "image/jpeg")}

    first = client.post(url, headers=headers, files=photo())
    assert first.status_code == 200, first.text
    first_key = _cover_key(db, job["id"])
    assert first_key and get_storage().exists(first_key)
    public = client.get(f"/api/job-openings/{job['slug']}").json()
    assert public["cover_url"] == first.json()["cover_url"]
    assert [j["cover_url"] for j in client.get("/api/job-openings").json()] == [public["cover_url"]]
    assert "cover_storage_key" not in public

    # Replacing it removes the old file.
    assert client.post(url, headers=headers, files=photo()).status_code == 200
    second_key = _cover_key(db, job["id"])
    assert second_key and second_key != first_key
    assert not get_storage().exists(first_key)

    removed = client.delete(url, headers=headers)
    assert removed.status_code == 200 and removed.json()["cover_url"] is None
    assert not get_storage().exists(second_key)
    assert client.get(f"/api/job-openings/{job['slug']}").json()["cover_url"] is None

    # Deleting the opening takes its thumbnail with it.
    assert client.post(url, headers=headers, files=photo()).status_code == 200
    last_key = _cover_key(db, job["id"])
    assert client.delete(f"/api/admin/job-openings/{job['id']}", headers=headers).status_code == 200
    assert last_key and not get_storage().exists(last_key)


def test_only_content_staff_set_a_thumbnail(client: TestClient, admin: User) -> None:
    manager = admin_headers(client)
    job = _create(client, manager)
    support = _invite(client, manager, "SUPPORT", "support-jobs-thumb@example.com")
    url = f"/api/admin/job-openings/{job['id']}/image"
    photo = {"file": ("thumb.jpg", make_image((600, 400)), "image/jpeg")}
    assert client.post(url, headers=support, files=photo).status_code == 403
    assert client.delete(url, headers=support).status_code == 403
    assert client.post(url, files=photo).status_code == 401
