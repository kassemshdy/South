"""The Telegram archive of what users save.

Asserted: it is inert without both variables; a user's save is posted with
its fields and files; an administrator's is not; a rollback posts nothing;
a password hash never leaves; the bot token never reaches the logs.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import SessionLocal
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services import telegram_archive
from app.services.telegram_archive import TelegramArchive
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar
from tests.test_registration import PNG_BYTES, _business_payload, _register

TOKEN = "123456:secret-bot-token"


class FakeTelegram:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.documents: list[bytes] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.startswith(f"/bot{TOKEN}/")
        if request.url.path.endswith("/sendMessage"):
            form = dict(httpx.QueryParams(request.content.decode()))
            self.messages.append(form["text"])
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
        client=httpx.Client(transport=httpx.MockTransport(fake.handler)),
        interval=0,
        autostart=False,
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


def test_an_application_is_posted_with_its_id_scan(
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

    text = "\n".join(fake.messages)
    assert "users created" in text
    assert "businesses created" in text
    assert "owner_verification_documents created" in text
    assert ar("business.applicant") in text
    assert ar("identity.full_name") in text
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

    text = "\n".join(fake.messages)
    assert "orders created" in text
    assert ar("order.customer") in text
    assert "+9613990600" in text
    assert ar("business.sweets_shop") in text, "the shop is named"


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
            actor="x", changes=[telegram_archive.Change("created", "orders", "1", {"a": "b"})]
        )
    )
    archive.drain()
    assert fake.messages
    assert TOKEN not in caplog.text
    assert "secret-bot-token" not in json.dumps([r.getMessage() for r in caplog.records])
