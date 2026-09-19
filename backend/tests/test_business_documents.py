"""A listing's official papers: optional, owner-scoped, never public.

Three properties are pinned here, and each one is the kind that decays
quietly:

- **Optional.** A business submits, is approved and is published with no
  paperwork at all. Plenty of real shops in the South have never been
  registered anywhere, and a requirement would lock out exactly the people the
  directory exists to serve. Nothing in the submit path may start consulting
  these.
- **Owner-scoped.** A document id from the request is never enough: every
  route loads the business through ``OwnedBusiness`` first, so one owner
  cannot read, attach to or delete from another's listing.
- **Never public.** A commercial register names the owner and the
  establishment's address. No public payload carries the documents, there is
  no url column to link, and the bytes come back only through the
  admin-gated download — the same boundary ``tests/test_identity.py`` keeps
  for the account holder's own fields.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.taxonomy import Category, Location
from tests.conftest import admin_headers, sign_in
from tests.samples import ar

OWNER_PHONE = "03810001"
OTHER_OWNER_PHONE = "03810002"


def pdf_bytes(body: bytes = b"commercial register") -> bytes:
    """Bytes that sniff as a PDF — the magic number is what the server reads,
    never the content type the client claims."""
    return b"%PDF-1.4\n" + body


def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), (240, 240, 230)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def business(
    client: TestClient, db: Session, category: Category, location: Location
) -> tuple[str, dict[str, str]]:
    """A listing complete enough to submit — so that when a test here submits
    it and nothing blocks, the reason is the absence of a document rule and
    not some unrelated missing field."""
    headers = sign_in(client, OWNER_PHONE)
    response = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.image_shop"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "whatsapp": "03810009",
        },
    )
    assert response.status_code == 201, response.text
    business_id = response.json()["id"]

    # A logo is required before review; set it directly rather than uploading.
    entity = db.get(Business, business_id)
    assert entity is not None
    entity.logo_url = "/media/test/logo.jpg"
    db.commit()

    return business_id, headers


def upload(
    client: TestClient,
    business_id: str,
    headers: dict[str, str],
    *,
    data: bytes | None = None,
    filename: str = "register.pdf",
    content_type: str = "application/pdf",
    label: str | None = None,
):
    return client.post(
        f"/api/businesses/{business_id}/documents",
        headers=headers,
        files={"file": (filename, data if data is not None else pdf_bytes(), content_type)},
        data={"label": label} if label is not None else {},
    )


# --- Optional ---------------------------------------------------------------


def test_a_business_submits_and_publishes_with_no_papers_at_all(
    client: TestClient, admin, business: tuple[str, dict[str, str]]
) -> None:
    """The property the whole feature hangs on.

    If a future readiness rule starts requiring a document, this is the test
    that says so — the shop with no paperwork is the one that most needs the
    listing.
    """
    business_id, headers = business

    readiness = client.get(f"/api/businesses/{business_id}/readiness", headers=headers)
    assert readiness.status_code == 200, readiness.text
    assert readiness.json() == []

    submitted = client.post(f"/api/businesses/{business_id}/submit", headers=headers)
    assert submitted.status_code == 200, submitted.text

    approved = client.post(
        f"/api/admin/businesses/{business_id}/approve", headers=admin_headers(client)
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["documents"] == []


# --- Storing ----------------------------------------------------------------


def test_the_owner_attaches_a_paper_and_gets_it_back_on_the_listing(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business

    response = upload(client, business_id, headers, label="Commercial register")
    assert response.status_code == 201, response.text

    documents = response.json()["documents"]
    assert len(documents) == 1
    assert documents[0]["content_type"] == "application/pdf"
    assert documents[0]["original_filename"] == "register.pdf"
    assert documents[0]["label"] == "Commercial register"
    # Metadata only: nothing here is a link to the bytes.
    assert "url" not in documents[0]
    assert "storage_key" not in documents[0]


def test_an_image_scan_is_accepted_as_readily_as_a_pdf(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    """Most people photograph the paper rather than scanning it to PDF."""
    business_id, headers = business
    response = upload(
        client,
        business_id,
        headers,
        data=jpeg_bytes(),
        filename="licence.jpg",
        content_type="image/jpeg",
    )
    assert response.status_code == 201, response.text
    assert response.json()["documents"][0]["content_type"] == "image/jpeg"


def test_the_claimed_content_type_is_not_believed(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    """A file is what its bytes say it is. Anything else would make the
    format check decorative."""
    business_id, headers = business
    response = upload(
        client,
        business_id,
        headers,
        data=b"MZ\x90\x00 not a document",
        filename="register.pdf",
        content_type="application/pdf",
    )
    assert response.status_code == 415


def test_the_per_listing_limit_is_enforced(
    client: TestClient, business: tuple[str, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    business_id, headers = business
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_business_documents", 2)

    assert upload(client, business_id, headers).status_code == 201
    assert upload(client, business_id, headers).status_code == 201

    refused = upload(client, business_id, headers)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "document_limit_reached"


def test_an_unreadable_file_is_refused_before_the_limit_is_consulted(
    client: TestClient, business: tuple[str, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An owner who sends something unreadable should be told that, not told
    they are out of slots."""
    business_id, headers = business
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_business_documents", 0)

    response = upload(client, business_id, headers, data=b"not a document at all")
    assert response.status_code == 415


# --- Owner scoping ----------------------------------------------------------


def test_another_owner_can_neither_attach_nor_delete(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    created = upload(client, business_id, headers)
    document_id = created.json()["documents"][0]["id"]

    intruder = sign_in(client, OTHER_OWNER_PHONE)

    # 404 rather than 403: the endpoint must not confirm the id exists to
    # someone with no business by it.
    assert upload(client, business_id, intruder).status_code == 404
    assert (
        client.delete(
            f"/api/businesses/{business_id}/documents/{document_id}", headers=intruder
        ).status_code
        == 404
    )

    still_there = client.get(f"/api/businesses/{business_id}/manage", headers=headers)
    assert len(still_there.json()["documents"]) == 1


def test_an_anonymous_request_cannot_attach_one(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, _ = business
    response = client.post(
        f"/api/businesses/{business_id}/documents",
        files={"file": ("register.pdf", pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 401


def test_the_owner_removes_a_paper(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    document_id = upload(client, business_id, headers).json()["documents"][0]["id"]

    response = client.delete(
        f"/api/businesses/{business_id}/documents/{document_id}", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["documents"] == []


# --- The public boundary ----------------------------------------------------


def test_no_public_payload_carries_the_papers(
    client: TestClient, admin, business: tuple[str, dict[str, str]]
) -> None:
    """The counterpart to ``tests/test_identity.py``: a document attached to
    an approved, published listing is still invisible to a visitor."""
    business_id, headers = business
    upload(client, business_id, headers, label="Commercial register")

    client.post(f"/api/businesses/{business_id}/submit", headers=headers)
    client.post(
        f"/api/admin/businesses/{business_id}/approve", headers=admin_headers(client)
    )

    slug = client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()["slug"]

    detail = client.get(f"/api/businesses/{slug}")
    assert detail.status_code == 200, detail.text
    assert "documents" not in detail.json()

    listing = client.get("/api/businesses").json()["items"][0]
    assert "documents" not in listing


def test_only_an_administrator_downloads_the_bytes(
    client: TestClient, admin, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    document_id = upload(client, business_id, headers).json()["documents"][0]["id"]
    path = f"/api/admin/businesses/{business_id}/documents/{document_id}/download"

    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers).status_code == 403

    response = client.get(path, headers=admin_headers(client))
    assert response.status_code == 200, response.text
    assert response.content == pdf_bytes()
    assert response.headers["content-type"].startswith("application/pdf")


def test_the_reviewer_sees_the_papers_on_the_review_payload(
    client: TestClient, admin, business: tuple[str, dict[str, str]]
) -> None:
    """Attaching a document is pointless if the person deciding never sees
    it, so the review payload carries the metadata without a second request."""
    business_id, headers = business
    upload(client, business_id, headers, label="Municipal licence")
    client.post(f"/api/businesses/{business_id}/submit", headers=headers)

    review = client.get(
        f"/api/admin/businesses/{business_id}", headers=admin_headers(client)
    )
    assert review.status_code == 200, review.text
    assert [d["label"] for d in review.json()["documents"]] == ["Municipal licence"]


def test_a_download_for_another_listings_document_is_not_found(
    client: TestClient, admin, business: tuple[str, dict[str, str]], category: Category
) -> None:
    """The business id in the path is a scoping clause, not decoration."""
    business_id, headers = business
    document_id = upload(client, business_id, headers).json()["documents"][0]["id"]

    other = client.post(
        "/api/businesses",
        headers=headers,
        json={"name": ar("business.second_shop"), "category_id": str(category.id)},
    ).json()["id"]

    response = client.get(
        f"/api/admin/businesses/{other}/documents/{document_id}/download",
        headers=admin_headers(client),
    )
    assert response.status_code == 404
