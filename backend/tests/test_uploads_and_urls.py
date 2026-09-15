"""Upload validation, URL sanitization and image processing."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.errors import ValidationError
from app.core.urls import normalize_social_url, normalize_url, youtube_video_id
from app.models.enums import SocialPlatform
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar


def make_image(size: tuple[int, int] = (1200, 900), fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 120, 60)).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def business(client: TestClient, category: Category, location: Location) -> tuple[str, dict[str, str]]:
    headers = sign_in(client, "03600001")
    response = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.image_shop"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    return response.json()["id"], headers


def test_valid_image_uploads_and_is_resized(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    response = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("cover.jpg", make_image((3000, 2000)), "image/jpeg")},
        data={"kind": "GALLERY"},
    )

    assert response.status_code == 201
    image = response.json()["images"][0]
    # Re-encoded and bounded, never stored at the original size.
    assert image["width"] is not None and image["width"] <= 1400
    assert image["url"].startswith("/media/")


def test_non_image_content_is_rejected(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    """A file claiming to be a JPEG but containing text must not be stored."""
    business_id, headers = business
    response = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("evil.jpg", b"<?php echo 'hello'; ?>", "image/jpeg")},
        data={"kind": "GALLERY"},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_disallowed_mime_type_is_rejected(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    response = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        data={"kind": "GALLERY"},
    )
    assert response.status_code == 415


def test_gallery_limit_is_enforced(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business

    for _ in range(10):
        uploaded = client.post(
            f"/api/businesses/{business_id}/images",
            headers=headers,
            files={"file": ("g.jpg", make_image((400, 400)), "image/jpeg")},
            data={"kind": "GALLERY"},
        )
        assert uploaded.status_code == 201

    eleventh = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("g.jpg", make_image((400, 400)), "image/jpeg")},
        data={"kind": "GALLERY"},
    )
    assert eleventh.status_code == 422
    assert eleventh.json()["error"]["code"] == "gallery_limit_reached"


def test_uploading_a_second_logo_replaces_the_first(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business

    for _ in range(2):
        client.post(
            f"/api/businesses/{business_id}/images",
            headers=headers,
            files={"file": ("logo.jpg", make_image((500, 500)), "image/jpeg")},
            data={"kind": "LOGO"},
        )

    detail = client.get(f"/api/businesses/{business_id}/manage", headers=headers).json()
    logos = [image for image in detail["images"] if image["kind"] == "LOGO"]
    assert len(logos) == 0  # gallery payload excludes logos
    assert detail["logo_url"] is not None


def test_png_with_transparency_is_flattened(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    buffer = io.BytesIO()
    Image.new("RGBA", (600, 600), (255, 0, 0, 120)).save(buffer, format="PNG")

    response = client.post(
        f"/api/businesses/{business_id}/images",
        headers=headers,
        files={"file": ("logo.png", buffer.getvalue(), "image/png")},
        data={"kind": "LOGO"},
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("platform", "url"),
    [
        (SocialPlatform.INSTAGRAM, "https://evil.example.com/phish"),
        (SocialPlatform.FACEBOOK, "not-a-url"),
        (SocialPlatform.TIKTOK, "https://tiktok.evil.com/x"),
    ],
)
def test_social_links_must_belong_to_their_platform(
    platform: SocialPlatform, url: str
) -> None:
    with pytest.raises(ValidationError):
        normalize_social_url(platform, url)


def test_javascript_urls_are_rejected() -> None:
    with pytest.raises(ValidationError):
        normalize_url("javascript:alert(1)")


def test_urls_are_normalized_and_credentials_stripped() -> None:
    assert normalize_url("example.com/shop") == "https://example.com/shop"
    assert normalize_url("https://user:secret@example.com/a#frag") == "https://example.com/a"


def test_social_link_saved_through_the_api_is_validated(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business

    rejected = client.put(
        f"/api/businesses/{business_id}",
        headers=headers,
        json={"social_links": [{"platform": "INSTAGRAM", "url": "https://evil.example.com"}]},
    )
    accepted = client.put(
        f"/api/businesses/{business_id}",
        headers=headers,
        json={"social_links": [{"platform": "INSTAGRAM", "url": "instagram.com/shop"}]},
    )

    assert rejected.status_code == 422
    assert accepted.status_code == 200
    assert accepted.json()["social_links"][0]["url"] == "https://instagram.com/shop"


# Every shape YouTube itself hands out, since an owner pastes whatever the
# share sheet gave them: a watch link with a timestamp, a youtu.be short
# link, a Short, a live URL, the mobile host, an embed.
@pytest.mark.parametrize(
    "link",
    [
        "https://www.youtube.com/watch?v=3Np8hKhrbB4",
        "youtube.com/watch?v=3Np8hKhrbB4&t=42s",
        "https://youtu.be/3Np8hKhrbB4",
        "https://youtu.be/3Np8hKhrbB4?t=10",
        "https://www.youtube.com/shorts/3Np8hKhrbB4",
        "https://m.youtube.com/watch?v=3Np8hKhrbB4",
        "https://www.youtube.com/live/3Np8hKhrbB4",
        "https://www.youtube-nocookie.com/embed/3Np8hKhrbB4",
        "  https://www.youtube.com/watch?v=3Np8hKhrbB4  ",
    ],
)
def test_every_youtube_link_shape_yields_the_bare_id(link: str) -> None:
    assert youtube_video_id(link) == "3Np8hKhrbB4"


@pytest.mark.parametrize(
    "link",
    [
        "https://vimeo.com/12345",
        "javascript:alert(1)",
        # A channel is not a video, and neither is the bare homepage.
        "https://www.youtube.com/channel/UCabcdefghij",
        "https://www.youtube.com/",
        # Too short to be an id, and a host that merely mentions YouTube in
        # its path — the case a substring check would wave through.
        "https://youtube.com/watch?v=short",
        "https://evil.example.com/youtube.com/watch?v=3Np8hKhrbB4",
    ],
)
def test_anything_that_is_not_a_youtube_video_is_rejected(link: str) -> None:
    with pytest.raises(ValidationError):
        youtube_video_id(link)


def test_owner_submits_a_video_link_and_the_listing_publishes_an_id(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    """The API takes a link and hands back an id, never the pasted string."""
    business_id, headers = business

    rejected = client.put(
        f"/api/businesses/{business_id}",
        headers=headers,
        json={"video_url": "https://vimeo.com/12345"},
    )
    accepted = client.put(
        f"/api/businesses/{business_id}",
        headers=headers,
        json={"video_url": "https://youtu.be/3Np8hKhrbB4?t=30"},
    )

    assert rejected.status_code == 422
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["youtube_video_id"] == "3Np8hKhrbB4"
    # The link itself is not stored, so it cannot be echoed back either.
    assert "video_url" not in body


def test_clearing_the_video_link_removes_the_id(
    client: TestClient, business: tuple[str, dict[str, str]]
) -> None:
    business_id, headers = business
    client.put(
        f"/api/businesses/{business_id}",
        headers=headers,
        json={"video_url": "https://www.youtube.com/watch?v=3Np8hKhrbB4"},
    )

    cleared = client.put(
        f"/api/businesses/{business_id}", headers=headers, json={"video_url": None}
    )

    assert cleared.status_code == 200
    assert cleared.json()["youtube_video_id"] is None
