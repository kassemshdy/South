"""Owner identity-document upload: validation, storage, and admin-only access."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import admin_headers, sign_in


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for tests\n"


def _jpeg_bytes() -> bytes:
    # A real minimal JPEG header (SOI marker) is enough for magic-byte sniffing.
    return b"\xff\xd8\xff\xe0" + b"\x00" * 32


def test_valid_pdf_upload_succeeds(client: TestClient) -> None:
    headers = sign_in(client, "03700001")
    response = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("id.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["content_type"] == "application/pdf"
    assert body["original_filename"] == "id.pdf"
    assert "url" not in body


def test_valid_jpeg_upload_succeeds(client: TestClient) -> None:
    headers = sign_in(client, "03700002")
    response = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("id.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["content_type"] == "image/jpeg"


def test_reupload_replaces_the_previous_document(client: TestClient) -> None:
    headers = sign_in(client, "03700003")
    me = client.get("/api/me", headers=headers).json()
    user_dir = Path(get_settings().storage_local_dir) / "owner-verification" / me["id"]

    first = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("first.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("second.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["content_type"] == "image/jpeg"

    meta = client.get("/api/me/verification-document", headers=headers)
    assert meta.json()["id"] == second.json()["id"]

    # Only one file should remain on disk for this user — the first was deleted.
    remaining_files = [p for p in user_dir.rglob("*") if p.is_file()]
    assert len(remaining_files) == 1


def test_content_not_matching_any_known_format_is_rejected(client: TestClient) -> None:
    headers = sign_in(client, "03700004")
    response = client.post(
        "/api/me/verification-document",
        headers=headers,
        # Claims to be a PDF; the bytes say otherwise. Sniffing must not trust
        # the client-supplied content type, same distrust ImageService applies.
        files={"file": ("fake.pdf", b"just some plain text", "application/pdf")},
    )
    assert response.status_code == 415, response.text
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_oversized_upload_is_rejected(client: TestClient) -> None:
    headers = sign_in(client, "03700005")
    settings = get_settings()
    oversized = _pdf_bytes() + b"0" * (settings.max_verification_doc_bytes + 1)
    response = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "payload_too_large"


def test_no_document_uploaded_reports_none_not_an_error(client: TestClient) -> None:
    headers = sign_in(client, "03700006")
    response = client.get("/api/me/verification-document", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_owner_cannot_reach_the_admin_download_endpoint(client: TestClient) -> None:
    owner_headers = sign_in(client, "03700007")
    response = client.get(
        "/api/admin/users/00000000-0000-0000-0000-000000000000/verification-document",
        headers=owner_headers,
    )
    assert response.status_code == 403


@pytest.mark.usefixtures("admin")
def test_admin_can_view_and_download_the_document(client: TestClient) -> None:
    owner_headers = sign_in(client, "03700008")
    me = client.get("/api/me", headers=owner_headers).json()
    upload = client.post(
        "/api/me/verification-document",
        headers=owner_headers,
        files={"file": ("id.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    admin_auth = admin_headers(client)

    meta = client.get(
        f"/api/admin/users/{me['id']}/verification-document", headers=admin_auth
    )
    assert meta.status_code == 200, meta.text
    assert meta.json()["content_type"] == "application/pdf"

    download = client.get(
        f"/api/admin/users/{me['id']}/verification-document/download",
        headers=admin_auth,
    )
    assert download.status_code == 200, download.text
    assert download.content == _pdf_bytes()
    assert download.headers["content-type"].startswith("application/pdf")
    assert "id.pdf" in download.headers["content-disposition"]


@pytest.mark.usefixtures("admin")
def test_admin_gets_404_for_a_user_with_no_document(client: TestClient) -> None:
    owner_headers = sign_in(client, "03700009")
    me = client.get("/api/me", headers=owner_headers).json()
    admin_auth = admin_headers(client)

    response = client.get(
        f"/api/admin/users/{me['id']}/verification-document", headers=admin_auth
    )
    assert response.status_code == 404


def test_cv_upload_is_separate_from_the_id_document(client: TestClient) -> None:
    """Both documents coexist: uploading one must not replace the other."""
    headers = sign_in(client, "03700010")
    identity = client.post(
        "/api/me/verification-document",
        headers=headers,
        files={"file": ("id.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert identity.status_code == 201, identity.text

    cv = client.post(
        "/api/me/cv-document",
        headers=headers,
        files={"file": ("cv.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert cv.status_code == 201, cv.text
    assert cv.json()["original_filename"] == "cv.jpg"
    assert "url" not in cv.json()

    assert client.get("/api/me/verification-document", headers=headers).json()[
        "content_type"
    ] == "application/pdf"
    assert client.get("/api/me/cv-document", headers=headers).json()[
        "content_type"
    ] == "image/jpeg"


def test_cv_reupload_replaces_only_the_cv(client: TestClient) -> None:
    headers = sign_in(client, "03700011")
    me = client.get("/api/me", headers=headers).json()
    cv_dir = Path(get_settings().storage_local_dir) / "owner-cv" / me["id"]

    for name in ("first.pdf", "second.pdf"):
        response = client.post(
            "/api/me/cv-document",
            headers=headers,
            files={"file": (name, _pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 201, response.text

    assert len(list(cv_dir.iterdir())) == 1
    assert (
        client.get("/api/me/cv-document", headers=headers).json()["original_filename"]
        == "second.pdf"
    )


def test_missing_cv_reads_as_null(client: TestClient) -> None:
    headers = sign_in(client, "03700012")
    response = client.get("/api/me/cv-document", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_owner_cannot_reach_the_admin_cv_endpoint(client: TestClient) -> None:
    owner_headers = sign_in(client, "03700013")
    me = client.get("/api/me", headers=owner_headers).json()
    client.post(
        "/api/me/cv-document",
        headers=owner_headers,
        files={"file": ("cv.pdf", _pdf_bytes(), "application/pdf")},
    )
    for path in (
        f"/api/admin/users/{me['id']}/cv-document",
        f"/api/admin/users/{me['id']}/cv-document/download",
    ):
        assert client.get(path, headers=owner_headers).status_code == 403


@pytest.mark.usefixtures("admin")
def test_admin_can_download_the_cv(client: TestClient) -> None:
    owner_headers = sign_in(client, "03700014")
    me = client.get("/api/me", headers=owner_headers).json()
    upload = client.post(
        "/api/me/cv-document",
        headers=owner_headers,
        files={"file": ("cv.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    admin_auth = admin_headers(client)
    download = client.get(
        f"/api/admin/users/{me['id']}/cv-document/download", headers=admin_auth
    )
    assert download.status_code == 200, download.text
    assert download.content == _pdf_bytes()
    assert "cv.pdf" in download.headers["content-disposition"]

    # An account with a CV but no ID scan still 404s on the ID endpoint —
    # the two are looked up independently.
    assert (
        client.get(
            f"/api/admin/users/{me['id']}/verification-document", headers=admin_auth
        ).status_code
        == 404
    )
