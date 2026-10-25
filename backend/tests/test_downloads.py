"""Downloading a file whose name is Arabic.

An applicant's ID scan named in Arabic made the administrator's download a
500: the name went into a Latin-1 header as it was. The header now carries an
ASCII fallback and the real name percent-encoded (RFC 6266).
"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.downloads import content_disposition
from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers
from tests.samples import ar
from tests.test_registration import PNG_BYTES, _business_payload, _register


def test_the_header_is_latin_1_and_keeps_the_real_name() -> None:
    name = ar("document.arabic_filename")
    header = content_disposition(name)
    header.encode("latin-1")
    assert 'filename="file.png"' in header
    assert unquote(header.split("filename*=UTF-8''")[1]) == name


def test_an_administrator_downloads_an_id_scan_named_in_arabic(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    name = ar("document.arabic_filename")
    response = _register(
        client,
        "business",
        _business_payload(category, location),
        document=(name, PNG_BYTES, "image/png"),
    )
    assert response.status_code == 202, response.text
    applicant = db.execute(select(User).where(User.phone_number.is_not(None))).scalars().all()
    owner = next(user for user in applicant if user.id != admin.id)

    download = client.get(
        f"/api/admin/users/{owner.id}/verification-document/download",
        headers=admin_headers(client),
    )

    assert download.status_code == 200, download.text
    assert download.content == PNG_BYTES
    assert unquote(download.headers["content-disposition"].split("UTF-8''")[1]) == name
