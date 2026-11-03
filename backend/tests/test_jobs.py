"""Job openings (29 Oct 2026): written by administrators. Since the jobs
redesign (31 Oct 2026) they are applied to by WhatsApp or a call, carry a
status apart from publishing, and count presses of their contact buttons."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import PRIVATE_MEDIA_FOLDERS
from app.models.job import JobApplication, JobContactClickDaily, JobOpening
from app.models.site_setting import SiteSetting
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


def test_a_draft_reaches_nobody_and_a_closed_opening_keeps_its_page(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    draft = _create(client, headers, publish=False)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    past_deadline = _create(client, headers, slug="closed", deadline=yesterday)
    filled = _create(client, headers, slug="filled")
    open_job = _create(client, headers, slug="open")
    changed = client.put(
        f"/api/admin/job-openings/{filled['id']}", headers=headers, json={"status": "FILLED"}
    )
    assert changed.status_code == 200 and changed.json()["status"] == "FILLED"

    listed = client.get("/api/job-openings").json()
    # Open first; the closed ones after it, still listed.
    assert listed[0]["slug"] == open_job["slug"] and listed[0]["status"] == "ACTIVE"
    assert {j["slug"]: j["status"] for j in listed[1:]} == {
        "closed": "UNAVAILABLE",
        "filled": "FILLED",
    }
    assert client.get(f"/api/job-openings/{draft['slug']}").status_code == 404
    page = client.get(f"/api/job-openings/{past_deadline['slug']}")
    assert page.status_code == 200 and page.json()["status"] == "UNAVAILABLE"
    # The saved status is untouched: the deadline alone closed it.
    [row] = [
        j
        for j in client.get("/api/admin/job-openings", headers=headers).json()
        if j["slug"] == "closed"
    ]
    assert row["saved_status"] == "ACTIVE" and row["status"] == "UNAVAILABLE"
    sitemap = client.get("/sitemap.xml").text
    assert "/vacancies/open<" in sitemap and "/vacancies/closed<" in sitemap


def test_nobody_applies_through_the_site_any_more(client: TestClient, admin: User) -> None:
    job = _create(client, admin_headers(client))
    sent = client.post(
        f"/api/job-openings/{job['slug']}/apply",
        data={"full_name": ar("order.customer"), "email": "a@example.com", "phone_number": "03123456"},
        files={"cv": ("cv.pdf", PDF, "application/pdf")},
    )
    assert sent.status_code in (404, 405)


def test_the_contact_number_is_the_openings_own_or_the_sites_whatsapp(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    db.add(SiteSetting(key="contact_whatsapp", value="81 995 107"))
    db.commit()
    fallback = _create(client, headers, slug="fallback")
    own = _create(
        client, headers, slug="own", contact_phone="70 123 456", contact_name=ar("order.customer")
    )
    assert client.get("/api/job-openings/fallback").json()["contact_phone"] == "+96181995107"
    body = client.get("/api/job-openings/own").json()
    assert body["contact_phone"] == "+96170123456" and body["whatsapp_enabled"] is True
    assert fallback["own_contact_phone"] is None
    bad = client.put(
        f"/api/admin/job-openings/{own['id']}", headers=headers, json={"contact_phone": "12"}
    )
    assert bad.status_code == 422


def test_contact_presses_are_counted_per_button_and_day_and_nothing_else(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    job = _create(client, headers)
    url = f"/api/job-openings/{job['slug']}/contact-click"
    for channel in ("WHATSAPP", "WHATSAPP", "CALL"):
        assert client.post(url, json={"channel": channel}).status_code == 204
    assert client.post(url, json={"channel": "EMAIL"}).status_code == 422

    stats = client.get(f"/api/admin/job-openings/{job['id']}/contact-clicks", headers=headers)
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert (body["whatsapp"], body["call"]) == (2, 1)
    assert len(body["days"]) == 1 and body["days"][0]["whatsapp"] == 2
    [row] = [
        j for j in client.get("/api/admin/job-openings", headers=headers).json() if j["id"] == job["id"]
    ]
    assert row["contact_clicks"] == 3

    # A filled opening shows no buttons, so it counts nothing.
    client.put(f"/api/admin/job-openings/{job['id']}", headers=headers, json={"status": "FILLED"})
    assert client.post(url, json={"channel": "CALL"}).status_code == 204
    assert (
        client.get(f"/api/admin/job-openings/{job['id']}/contact-clicks", headers=headers).json()[
            "call"
        ]
        == 1
    )
    columns = {column.name for column in JobContactClickDaily.__table__.columns}
    assert columns == {"id", "job_id", "channel", "day", "clicks"}, "nothing about who pressed"


def test_deleting_an_opening_removes_applications_sent_before_the_redesign(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    job = _create(client, headers)
    db.add(
        JobApplication(
            job_id=job["id"],
            full_name=ar("order.customer"),
            email="applicant@example.com",
            phone_number="+9613123456",
            storage_key=f"{FOLDER}/missing.pdf",
            content_type="application/pdf",
            size_bytes=len(PDF),
        )
    )
    db.commit()
    assert client.delete(f"/api/admin/job-openings/{job['id']}", headers=headers).status_code == 200
    assert db.query(JobApplication).count() == 0


def test_applications_sent_before_the_redesign_stay_readable_by_reviewers(
    client: TestClient, db: Session, admin: User
) -> None:
    """Applying moved to WhatsApp and calls, but what people already sent is
    not lost: staff still list it, and reviewers read the CV (the owners'
    decision, 3 Nov 2026)."""
    manager = admin_headers(client)
    job = _create(client, manager)
    key = f"{FOLDER}/kept.pdf"
    get_storage().save(key=key, data=PDF, content_type="application/pdf")
    db.add(
        JobApplication(
            job_id=job["id"],
            full_name=ar("order.customer"),
            email="applicant@example.com",
            phone_number="+9613123456",
            storage_key=key,
            original_filename="cv.pdf",
            content_type="application/pdf",
            size_bytes=len(PDF),
        )
    )
    db.commit()

    listed = client.get("/api/admin/job-openings", headers=manager).json()
    assert listed[0]["application_count"] == 1
    rows = client.get(f"/api/admin/job-openings/{job['id']}/applications", headers=manager)
    assert rows.status_code == 200 and rows.json()[0]["email"] == "applicant@example.com"
    cv = f"/api/admin/job-openings/{job['id']}/applications/{rows.json()[0]['id']}/cv"
    assert client.get(cv, headers=manager).content == PDF

    support = _invite(client, manager, "SUPPORT", "support-cv@example.com")
    assert client.get(cv, headers=support).status_code == 403
    assert client.get(cv).status_code == 401


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
