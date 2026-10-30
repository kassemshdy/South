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
from email import policy as email_policy
from email.parser import BytesParser

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.i18n import translate
from app.database.session import SessionLocal
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.services import telegram_archive
from app.services.telegram_archive import Batch, TelegramArchive
from tests.conftest import admin_headers, post_item, sign_in
from tests.samples import ar
from tests.test_registration import APPLICANT_E164, PNG_BYTES, _business_payload, _register

TOKEN = "123456:secret-bot-token"


def label(name: str) -> str:
    return translate(f"telegram.label.{name}", locale="ar")


SITE = "https://site.test"


def _multipart_field(request: httpx.Request, name: str) -> str:
    """One text field of a multipart request, as Telegram would read it."""
    message = BytesParser(policy=email_policy.HTTP).parsebytes(
        f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + request.content
    )
    for part in message.iter_parts():
        if part.get_param("name", header="content-disposition") == name:
            return bytes(part.get_payload(decode=True)).decode("utf-8")
    raise AssertionError(f"no {name} field in the request")


class FakeTelegram:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.documents: list[bytes] = []
        self.photos: list[bytes] = []
        #: The text a photo carries: a listing with a logo is posted as that
        #: photo, and every business application has one now.
        self.captions: list[str] = []

    @property
    def texts(self) -> list[str]:
        """Everything posted as words, whether a message or a caption."""
        return self.messages + self.captions

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.startswith(f"/bot{TOKEN}/")
        if request.url.path.endswith("/sendMessage"):
            form = dict(httpx.QueryParams(request.content.decode()))
            assert form["parse_mode"] == "HTML"
            # No preview card under the admin link (the owners' request).
            assert json.loads(form["link_preview_options"]) == {"is_disabled": True}
            self.messages.append(form["text"])
        elif request.url.path.endswith("/sendPhoto"):
            self.photos.append(request.content)
            self.captions.append(_multipart_field(request, "caption"))
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
        shop=telegram_archive.shop_lookup(SessionLocal),
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
    assert lines[0] == f"<b>{translate('telegram.kind.shop', locale='ar')}</b>"
    assert lines[1] == f"{label('name')}: {ar('identity.full_name')}"
    assert lines[2] == f"{label('phone')}: {APPLICANT_E164}"
    assert lines[-1].startswith(f"{label('link')}: /admin/businesses/")
    assert ar("identity.residence_place") not in message, "no identity fields"
    assert "1986" not in message, "no identity fields"
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
    text = "\n".join(fake.texts)
    assert ar("identity.full_name") in text
    assert APPLICANT_E164 in text
    assert f"{label('link')}: {SITE}/admin/businesses/{business_id}" in text
    assert f"{label('shop')}: <b>{ar('business.applicant')}</b>" in text
    assert "password_hash" not in text
    # The ID scan, beside the logo's own files (every stored file goes).
    scans = [document for document in fake.documents if b"/logo/" not in document]
    assert len(scans) == 1, "the ID scan is attached"


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
    assert message.startswith(f"<b>{translate('telegram.kind.order', locale='ar')}</b>")
    assert ar("order.customer") in message
    assert "+9613990600" in message
    assert f"{label('shop')}: <b>{ar('business.sweets_shop')}</b>" in message
    assert f"{ar('item.generic')} × 2" in message, "what was ordered"
    assert message.endswith(f"{label('link')}: {SITE}/admin/orders")


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
    text = "\n".join(fake.texts)
    assert translate("telegram.past", locale="ar") in text.splitlines()[0]
    assert ar("identity.full_name") in text
    assert APPLICANT_E164 in text
    assert f"{SITE}/admin/businesses/{business.id}" in text
    assert f"{label('shop')}: <b>{ar('business.applicant')}</b>" in text
    # The ID scan, beside the logo's own files (every stored file goes).
    scans = [document for document in fake.documents if b"/logo/" not in document]
    assert len(scans) == 1, "the ID scan is attached"

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
            name="Shop one",
            logo_key="logos/b1.png",
            instagram="https://instagram.com/shop",
            facebook="https://facebook.com/shop",
        ),
        "b2": telegram_archive.Shop(name="Shop two", instagram="https://instagram.com/other"),
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
                changes=[telegram_archive.Change("created", "businesses", business_id)],
            )
        )

    (photo,) = fake.photos
    assert b"LOGO:logos/b1.png" in photo
    caption = photo.decode("utf-8", errors="ignore")
    assert f"{SITE}/admin/businesses/b1" in caption
    assert "https://instagram.com/shop" in caption
    assert "https://facebook.com/shop" in caption
    assert "Shop one" in caption
    (message,) = fake.messages
    assert f"{label('shop')}: <b>Shop two</b>" in message
    assert f"{label('instagram')}: https://instagram.com/other" in message
    assert label("facebook") not in message, "no line for a page it does not have"


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


def test_the_title_shop_product_and_review_are_bold_and_typed_text_is_escaped() -> None:
    """Telegram reads the messages as HTML: the title, shop, product and a
    review's text in bold, and anything a visitor typed escaped so it cannot
    add markup of its own."""
    archive = TelegramArchive(
        token=TOKEN, chat_id="-100", read_file=lambda key: b"", autostart=False
    )
    change = telegram_archive.Change(
        action="created",
        table="testimonials",
        row_id="t1",
        fields={"author_name": "Sam <b>", "rating": "5", "body": "Great & <i>fresh</i>"},
    )
    message = archive.render(telegram_archive.Batch(name="Sam <b>", phone=None, changes=[change]))
    assert message is not None
    first, *rest = message.text.splitlines()
    assert first == f"<b>{translate('telegram.kind.review', locale='ar')}</b>"
    assert f"{label('name')}: Sam &lt;b&gt;" in rest
    assert f"{label('text')}: <b>Great &amp; &lt;i&gt;fresh&lt;/i&gt;</b>" in rest


def test_a_shop_description_keeps_its_line_breaks() -> None:
    """An owner's description is posted with the lines they typed, not run
    together onto one line."""
    archive = TelegramArchive(
        token=TOKEN, chat_id="-100", read_file=lambda key: b"", autostart=False
    )
    change = telegram_archive.Change(
        action="created",
        table="businesses",
        row_id="b1",
        fields={"name": "Shop", "short_description": "first line\nsecond line"},
    )
    message = archive.render(telegram_archive.Batch(name="Sam", phone=None, changes=[change]))
    assert message is not None
    assert f"{label('description')}: first line\nsecond line" in message.text


def test_a_network_failure_logs_no_traceback_token_or_phone(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A dropped connection used to propagate to ``logger.exception``, whose
    traceback frames -- and so the error report -- hold the bot URL (with its
    token) and the message (with the owner's phone)."""

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    archive = TelegramArchive(
        token=TOKEN,
        chat_id="-100",
        read_file=lambda key: b"",
        base_url=SITE,
        client=httpx.Client(transport=httpx.MockTransport(unreachable)),
        interval=0,
        autostart=False,
    )
    caplog.set_level(logging.DEBUG)
    archive.submit(
        telegram_archive.Batch(
            name="x",
            phone="+96170111222",
            changes=[telegram_archive.Change("created", "orders", "1", {"a": "b"})],
        )
    )
    archive.drain()
    assert all(record.exc_info is None for record in caplog.records)
    assert TOKEN not in caplog.text
    assert "+96170111222" not in caplog.text
