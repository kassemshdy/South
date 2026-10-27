"""The Telegram archive of what users save.

Asserted: it is inert without both variables; a user's save is posted as
their name, their phone and a link to the admin screen that reviews it, and
nothing else; files only when turned on; an administrator's save is not
posted; a rollback posts nothing; the bot token never reaches the logs.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import SessionLocal
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services import telegram_archive
from app.services.telegram_archive import Batch, TelegramArchive
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar
from tests.test_registration import APPLICANT_E164, PNG_BYTES, _business_payload, _register

TOKEN = "123456:secret-bot-token"
SITE = "https://site.test"


class FakeTelegram:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.documents: list[bytes] = []
        self.photos: list[bytes] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.startswith(f"/bot{TOKEN}/")
        if request.url.path.endswith("/sendMessage"):
            form = dict(httpx.QueryParams(request.content.decode()))
            self.messages.append(form["text"])
        elif request.url.path.endswith("/sendPhoto"):
            self.photos.append(request.content)
        else:
            self.documents.append(request.content)
        return httpx.Response(200, json={"ok": True})


@pytest.fixture
def telegram() -> Iterator[tuple[FakeTelegram, TelegramArchive]]:
    fake = FakeTelegram()
    archive = TelegramArchive(
        token=TOKEN,
        chat_id="-100",
        read_file=lambda key: b"FILE:" + key.encode(),
        lookup=telegram_archive.context_lookup(SessionLocal),
        base_url=SITE,
        client=httpx.Client(transport=httpx.MockTransport(fake.handler)),
        interval=0,
        autostart=False,
        send_files=True,
    )
    telegram_archive.install_hooks(SessionLocal)
    telegram_archive.set_archive(archive)
    try:
        yield fake, archive
    finally:
        telegram_archive.set_archive(None)


def test_unconfigured_it_sends_nothing() -> None:
    telegram_archive.set_archive(None)
    settings = Settings(telegram_bot_token=None, telegram_chat_id="-1")
    telegram_archive.configure(settings, SessionLocal)
    assert telegram_archive._archive is None


def test_by_default_only_text_is_sent(
    client: TestClient,
    category: Category,
    location: Location,
) -> None:
    """Name, phone and review link only: no other field of the application,
    and no ID scan until TELEGRAM_SEND_FILES is turned on."""
    fake = FakeTelegram()
    archive = TelegramArchive(
        token=TOKEN,
        chat_id="-100",
        read_file=lambda key: b"FILE",
        client=httpx.Client(transport=httpx.MockTransport(fake.handler)),
        interval=0,
        autostart=False,
    )
    telegram_archive.install_hooks(SessionLocal)
    telegram_archive.set_archive(archive)
    try:
        response = _register(
            client,
            "business",
            _business_payload(category, location),
            document=("id.png", PNG_BYTES, "image/png"),
        )
        assert response.status_code == 202, response.text
        archive.drain()
    finally:
        telegram_archive.set_archive(None)

    (message,) = fake.messages
    lines = message.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("🆕🏪 "), "new, and about a shop"
    assert ar("identity.full_name") in lines[0]
    assert lines[1] == f"📞 {APPLICANT_E164}"
    assert lines[2].startswith("🔗 /admin/businesses/")
    assert ar("business.applicant") not in message, "no listing fields"
    assert ar("identity.residence_place") not in message, "no identity fields"
    assert fake.documents == []


def test_with_files_on_an_application_is_posted_with_its_id_scan(
    client: TestClient,
    category: Category,
    location: Location,
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    fake, archive = telegram
    response = _register(
        client,
        "business",
        _business_payload(category, location),
        document=("id.png", PNG_BYTES, "image/png"),
    )
    assert response.status_code == 202, response.text
    archive.drain()

    from app.models.business import Business

    with SessionLocal() as session:
        business_id = session.execute(select(Business.id)).scalar_one()
    text = "\n".join(fake.messages)
    assert ar("identity.full_name") in text
    assert APPLICANT_E164 in text
    assert f"🔗 {SITE}/admin/businesses/{business_id}" in text
    assert "password_hash" not in text
    assert len(fake.documents) == 1, "the ID scan is attached"


def test_an_order_is_posted(
    client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    fake, archive = telegram
    headers = sign_in(client, "03990501")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.sweets_shop"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    business_id = created.json()["id"]
    item = post_item(
        client,
        f"/api/businesses/{business_id}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "2.00", "currency": "USD"},
    ).json()
    archive.drain()
    products = "\n".join(fake.messages)
    assert "+9613990501" in products, "the signed-in owner's phone"
    assert f"{SITE}/admin/businesses/{business_id}" in products
    fake.messages.clear()

    from app.models.business import Business
    from app.models.enums import BusinessStatus

    entity = db.get(Business, business_id)
    assert entity is not None
    entity.status = BusinessStatus.APPROVED
    db.commit()

    placed = client.post(
        f"/api/businesses/{entity.slug}/orders",
        json={
            "customer_name": ar("order.customer"),
            "customer_phone": "03990600",
            "lines": [{"item_id": item["id"], "quantity": 2}],
        },
    )
    assert placed.status_code == 201, placed.text
    archive.drain()

    (message,) = fake.messages
    assert message.startswith("🆕🛒 ")
    assert ar("order.customer") in message
    assert "+9613990600" in message
    assert message.endswith(f"🔗 {SITE}/admin/orders")


def test_an_administrators_saves_are_not_posted(
    client: TestClient,
    admin: User,
    category: Category,
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    fake, archive = telegram
    headers = admin_headers(client)
    client.patch("/api/me", headers=headers, json={"display_name": "Admin"})
    archive.drain()
    assert fake.messages == []


def test_a_rolled_back_save_is_not_posted(
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    fake, archive = telegram
    from app.database.session import ARCHIVE_SESSION_FLAG
    from app.models.enums import UserRole

    with SessionLocal() as session:
        session.info[ARCHIVE_SESSION_FLAG] = True
        session.add(User(phone_number="+9613990700", role=UserRole.OWNER))
        session.flush()
        session.rollback()
    archive.drain()
    assert fake.messages == []


def test_the_bot_token_never_reaches_the_logs(
    caplog: pytest.LogCaptureFixture,
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    fake, archive = telegram
    caplog.set_level(logging.DEBUG)
    archive.submit(
        telegram_archive.Batch(
            name="x",
            phone=None,
            changes=[telegram_archive.Change("created", "orders", "1", {"a": "b"})],
        )
    )
    archive.drain()
    assert fake.messages
    assert TOKEN not in caplog.text
    assert "secret-bot-token" not in json.dumps([r.getMessage() for r in caplog.records])


def test_the_backfill_sends_a_business_with_its_owner_and_id_scan_once(
    client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    telegram: tuple[FakeTelegram, TelegramArchive],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Past data: one business, sent as its owner's name, phone and review
    link with the ID scan, and recorded so a second run sends nothing."""
    from app.models.business import Business
    from scripts import telegram_backfill

    fake, archive = telegram
    response = _register(
        client,
        "business",
        _business_payload(category, location),
        document=("id.png", PNG_BYTES, "image/png"),
    )
    assert response.status_code == 202, response.text
    telegram_archive.set_archive(None)  # only the backfill speaks from here

    business = db.execute(select(Business)).scalar_one()
    batch = telegram_backfill.business_batch(db, business)
    archive.send(batch)
    text = "\n".join(fake.messages)
    assert text.startswith("↩️🆕🏪 ") and ar("identity.full_name") in text
    assert APPLICANT_E164 in text
    assert f"{SITE}/admin/businesses/{business.id}" in text
    assert ar("business.applicant") not in text
    assert len(fake.documents) == 1, "the ID scan is attached"

    sent: list[Batch] = []
    monkeypatch.setenv("TELEGRAM_BACKFILL", "1")
    monkeypatch.setattr(
        telegram_backfill,
        "get_settings",
        lambda: Settings(telegram_bot_token=TOKEN, telegram_chat_id="-100"),
    )
    monkeypatch.setattr(TelegramArchive, "send", lambda self, batch: sent.append(batch))
    telegram_backfill.main()
    telegram_backfill.main()
    assert len(sent) == 1, "a business is sent once, however often the job runs"


def test_a_business_is_posted_with_its_logo_and_social_pages() -> None:
    """The logo is the photo, the Instagram and Facebook pages follow the
    link in its caption; with no logo the same lines go as text."""
    fake = FakeTelegram()
    shops = {
        "b1": telegram_archive.Shop(
            logo_key="logos/b1.png",
            links=["📷 https://instagram.com/shop", "📘 https://facebook.com/shop"],
        ),
        "b2": telegram_archive.Shop(links=["📷 https://instagram.com/other"]),
    }
    archive = TelegramArchive(
        token=TOKEN,
        chat_id="-100",
        read_file=lambda key: b"LOGO:" + key.encode(),
        shop=shops.get,
        base_url=SITE,
        client=httpx.Client(transport=httpx.MockTransport(fake.handler)),
        interval=0,
        autostart=False,
    )
    for business_id in shops:
        archive.send(
            Batch(
                name="n",
                phone="+9613000000",
                changes=[telegram_archive.Change("updated", "businesses", business_id)],
            )
        )

    (photo,) = fake.photos
    assert b"LOGO:logos/b1.png" in photo
    caption = photo.decode("utf-8", errors="ignore")
    assert f"{SITE}/admin/businesses/b1" in caption
    assert "https://instagram.com/shop" in caption
    assert "https://facebook.com/shop" in caption
    (message,) = fake.messages
    assert message.endswith(f"{SITE}/admin/businesses/b2\n📷 https://instagram.com/other")


def test_only_new_things_are_posted_not_edits(
    client: TestClient,
    telegram: tuple[FakeTelegram, TelegramArchive],
) -> None:
    """The owners asked for creations only: an owner editing their account
    posts nothing."""
    fake, archive = telegram
    headers = sign_in(client, "03990801")
    archive.drain()
    fake.messages.clear()

    response = client.patch("/api/me", headers=headers, json={"display_name": "Owner"})
    assert response.status_code == 200, response.text
    archive.drain()
    assert fake.messages == []
