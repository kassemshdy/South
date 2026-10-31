"""Janoubona as a client of the shared Shopify Connector.

The connector (its own repository) is replaced by an ``httpx.MockTransport``
that answers like it; its webhooks are signed here the way it signs them.
What is pinned:

- the routes do not exist until the connector is configured;
- connecting asks the connector, only for an approved listing, and returns
  the owner to their own dashboard;
- a webhook is believed only with the connector's signature, and a fresh one;
- a product edit on a connected shop queues one push, in the same
  transaction -- and on any other shop, nothing; the push sends what a
  visitor would see, with absolute https photos;
- buy links are public only while the connector says the store is
  connected.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import uuid
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.integrations import get_http_client
from app.core.config import Settings, get_settings
from app.database.session import SessionLocal
from app.main import create_app
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.integration import IntegrationOutbox, ItemLink, StoreLink
from app.models.taxonomy import Category, Location
from app.services import connector, outbox
from tests.conftest import post_item, sign_in
from tests.samples import ar

OWNER_PHONE = "03880001"
OTHER_PHONE = "03880002"
WEBHOOK_SECRET = "whsec_test"
CONNECTOR = "https://connector.test"


def connector_settings(**overrides: object) -> Settings:
    return get_settings().model_copy(
        update={
            "connector_url": CONNECTOR,
            "connector_api_key": "sc_live_test",
            "connector_webhook_secret": WEBHOOK_SECRET,
            # The worker never runs on its own in a test; drain does.
            "integration_outbox_poll_seconds": 3600,
            "public_base_url": "https://janoubona.test",
            **overrides,
        }
    )


class FakeConnector:
    """Answers like the Shopify Connector's /v1 API."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.stores: dict[str, dict[str, object]] = {}
        self.down = False

    def calls(self, method: str, pattern: str) -> list[httpx.Request]:
        return [
            r for r in self.requests if r.method == method and re.search(pattern, r.url.path)
        ]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.down:
            return httpx.Response(502, text="bad gateway")
        assert request.headers["Authorization"] == "Bearer sc_live_test"
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        if path == "/v1/tenant":
            return httpx.Response(200, json={
                "slug": "janoubona", "name": "Janoubona", "signup_url": "https://signup.test",
                "subdomain_base": "janoubona.net", "subdomains_available": True})
        m = re.fullmatch(r"/v1/stores/([^/]+)(/.*)?", path)
        assert m, path
        ref, rest = m.group(1), m.group(2) or ""
        if rest == "/connect":
            if "evil" in body["shop"]:
                return httpx.Response(422, json={"error": {"code": "bad_shop", "message": "x"}})
            return httpx.Response(200, json={
                "authorize_url": f"https://{body['shop']}/admin/oauth/authorize?r={ref}"})
        if rest == "/subdomain":
            if body["subdomain"] == "www":
                return httpx.Response(422, json={
                    "error": {"code": "reserved_subdomain", "message": "x"}})
            store = self.stores.setdefault(ref, {"status": "CONNECTED"})
            store.update(subdomain=body["subdomain"],
                         subdomain_hostname=f"{body['subdomain']}.janoubona.net")
            return httpx.Response(200, json={"store_ref": ref, **store})
        if rest.startswith("/products/"):
            product_ref = rest.split("/")[2]
            if request.method == "DELETE":
                return httpx.Response(202, json={"queued": 1})
            return httpx.Response(202, json={
                "store_ref": ref, "product_ref": product_ref, "state": "QUEUED",
                "handle": None, "active": False, "buy_url": None, "error": None})
        if request.method == "DELETE":
            self.stores.pop(ref, None)
            return httpx.Response(204)
        if ref not in self.stores:
            return httpx.Response(404, json={"error": {"code": "store_not_found", "message": "x"}})
        return httpx.Response(200, json={"store_ref": ref, "jobs_pending": 0, **self.stores[ref]})


@pytest.fixture
def fake() -> FakeConnector:
    return FakeConnector()


@pytest.fixture
def settings() -> Settings:
    return connector_settings()


@pytest.fixture
def shop_client(settings: Settings, fake: FakeConnector) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings

    def http() -> Iterator[httpx.Client]:
        with httpx.Client(transport=httpx.MockTransport(fake)) as client:
            yield client

    app.dependency_overrides[get_http_client] = http
    with TestClient(app) as test_client:
        yield test_client
    outbox.uninstall_hooks(SessionLocal)


def approved_business(
    client: TestClient, db: Session, headers: dict[str, str], category: Category, location: Location
) -> Business:
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.first"),
            "short_description": ar("business.generic_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "latitude": 33.27,
            "longitude": 35.2,
        },
    )
    assert created.status_code == 201, created.text
    business = db.get(Business, uuid.UUID(created.json()["id"]))
    assert business is not None
    business.status = BusinessStatus.APPROVED
    db.commit()
    return business


def add_item(
    client: TestClient, business: Business, headers: dict[str, str], *, currency: str = "USD"
) -> str:
    created = post_item(
        client,
        f"/api/businesses/{business.id}/items",
        headers=headers,
        json={"title": ar("item.zaatar"), "price": "4.50", "currency": currency},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def webhook(
    client: TestClient,
    event: str,
    data: dict[str, object],
    *,
    secret: str = WEBHOOK_SECRET,
    age: int = 0,
) -> httpx.Response:
    body = json.dumps({"id": str(uuid.uuid4()), "event": event, "data": data}).encode()
    t = int(time.time()) - age
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/integrations/connector/webhooks",
        content=body,
        headers={"X-Connector-Signature": f"t={t},v1={mac}", "Content-Type": "application/json"},
    )


def connected(business: Business, **extra: object) -> dict[str, object]:
    return {
        "store_ref": str(business.id),
        "status": "CONNECTED",
        "shop_domain": "souk.myshopify.com",
        "storefront_url": "https://souk.example.com",
        "subdomain": None,
        "subdomain_hostname": None,
        "currency": "USD",
        "last_error": None,
        **extra,
    }


def drain(settings: Settings, fake: FakeConnector) -> int:
    with httpx.Client(transport=httpx.MockTransport(fake)) as http:
        return outbox.drain_once(SessionLocal, connector.make_handlers(settings, http))


def pending(db: Session) -> list[IntegrationOutbox]:
    db.expire_all()
    return list(db.scalars(select(IntegrationOutbox).where(IntegrationOutbox.done_at.is_(None))))


# --- Off until configured ----------------------------------------------------


def test_every_route_is_absent_without_configuration(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, OWNER_PHONE)
    business = approved_business(client, db, headers, category, location)
    assert client.get(f"/api/businesses/{business.id}/shopify", headers=headers).status_code == 404
    assert client.post("/api/integrations/connector/webhooks", content=b"{}").status_code == 404


def test_production_refuses_a_half_configured_connector() -> None:
    hardened = get_settings().model_copy(
        update={"app_env": "production", "secret_key": "s" * 40, "admin_password": "Strong!pass1"}
    )
    with pytest.raises(RuntimeError, match="CONNECTOR_API_KEY"):
        hardened.model_copy(update={"connector_url": CONNECTOR}).enforce_production_safety()
    with pytest.raises(RuntimeError, match="https"):
        hardened.model_copy(
            update={
                "connector_url": "http://connector.test",
                "connector_api_key": "k",
                "connector_webhook_secret": "s",
            }
        ).enforce_production_safety()


# --- Connecting ----------------------------------------------------------------


def test_connecting_asks_the_connector_and_returns_to_the_owners_dashboard(
    shop_client: TestClient,
    db: Session,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    r = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": "souk"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["authorize_url"].startswith("https://souk/admin/oauth/authorize")
    sent = json.loads(fake.calls("POST", r"/connect$")[0].content)
    assert sent["return_url"] == (
        f"https://janoubona.test/dashboard/businesses/{business.id}/items"
    )


def test_install_refuses_a_listing_that_is_not_approved(
    shop_client: TestClient,
    db: Session,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    business.status = BusinessStatus.PENDING_REVIEW
    db.commit()
    r = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": "souk"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "shopify_not_approved"
    assert fake.requests == []


def test_the_connectors_refusal_reaches_the_owner_in_our_words(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    r = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": "evil"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "shopify_bad_shop"


def test_another_owner_cannot_reach_the_connection(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    other = sign_in(shop_client, OTHER_PHONE)
    r = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=other, json={"shop": "souk"}
    )
    assert r.status_code == 404


def test_the_card_shows_the_connectors_view_and_survives_it_being_down(
    shop_client: TestClient,
    db: Session,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    url = f"/api/businesses/{business.id}/shopify"
    before = shop_client.get(url, headers=headers).json()
    assert before["connected"] is False
    assert before["signup_url"] == "https://signup.test"
    assert before["subdomains_available"] is True
    fake.stores[str(business.id)] = connected(business)
    after = shop_client.get(url, headers=headers).json()
    assert after["connected"] is True
    assert after["storefront_url"] == "https://souk.example.com"
    fake.down = True
    assert shop_client.get(url, headers=headers).status_code == 503


# --- The connector's webhooks -----------------------------------------------------


@pytest.mark.parametrize(("secret", "age"), [("whsec_forged", 0), (WEBHOOK_SECRET, 3600)])
def test_a_webhook_without_a_fresh_valid_signature_is_refused(
    shop_client: TestClient,
    db: Session,
    category: Category,
    location: Location,
    secret: str,
    age: int,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    r = webhook(shop_client, "store.connected", connected(business), secret=secret, age=age)
    assert r.status_code == 401
    assert db.scalars(select(StoreLink)).first() is None


def test_store_connected_mirrors_the_store_and_queues_every_product(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    add_item(shop_client, business, headers)
    assert pending(db) == []  # nothing queued before the store is connected

    assert webhook(shop_client, "store.connected", connected(business)).status_code == 200
    link = db.scalars(select(StoreLink)).one()
    assert link.is_live and link.storefront_url == "https://souk.example.com"
    assert len(pending(db)) == 2

    assert drain(settings, fake) == 2
    puts = fake.calls("PUT", rf"/v1/stores/{business.id}/products/")
    assert len(puts) == 2
    sent = json.loads(next(r for r in puts if r.url.path.endswith(item_id)).content)
    assert sent["price"] == "4.50" and sent["currency"] == "USD"
    assert sent["available"] is True
    assert sent["images"]
    assert all(u.startswith("https://janoubona.test/") for u in sent["images"])
    assert "token" not in json.dumps(sent)


def test_an_edit_on_a_connected_shop_queues_one_push_and_others_queue_nothing(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    webhook(shop_client, "store.connected", connected(business))
    drain(settings, fake)
    assert pending(db) == []

    edited = shop_client.put(
        f"/api/businesses/{business.id}/items/{item_id}", headers=headers, json={"price": "6.00"}
    )
    assert edited.status_code == 200, edited.text
    queued = pending(db)
    assert [(e.kind, e.payload["item_id"]) for e in queued] == [(outbox.ITEM_UPSERT, item_id)]

    other_headers = sign_in(shop_client, OTHER_PHONE)
    other = approved_business(shop_client, db, other_headers, category, location)
    add_item(shop_client, other, other_headers)
    assert len(pending(db)) == 1


def test_buy_links_follow_what_the_connector_reports(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    webhook(shop_client, "store.connected", connected(business))
    drain(settings, fake)
    buy = "https://souk.example.com/products/zaatar"
    webhook(
        shop_client,
        "product.synced",
        {
            "store_ref": str(business.id),
            "product_ref": item_id,
            "state": "SYNCED",
            "handle": "zaatar",
            "active": True,
            "buy_url": buy,
            "error": None,
        },
    )

    item = db.get(BusinessItem, uuid.UUID(item_id))
    assert item is not None
    page = shop_client.get(f"/api/businesses/{business.slug}").json()
    assert page["online_store_url"] == "https://souk.example.com"
    assert shop_client.get(f"/api/items/{item.slug}").json()["buy_url"] == buy

    webhook(
        shop_client,
        "store.updated",
        connected(business, status="UNINSTALLED", storefront_url=None),
    )
    assert shop_client.get(f"/api/businesses/{business.slug}").json()["online_store_url"] is None
    assert shop_client.get(f"/api/items/{item.slug}").json()["buy_url"] is None


def test_a_webhook_for_another_businesss_product_changes_nothing(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    other_headers = sign_in(shop_client, OTHER_PHONE)
    other = approved_business(shop_client, db, other_headers, category, location)
    other_item = add_item(shop_client, other, other_headers)
    webhook(
        shop_client,
        "product.synced",
        {
            "store_ref": str(business.id),
            "product_ref": other_item,
            "state": "SYNCED",
            "handle": "x",
            "active": True,
            "buy_url": "https://evil.test/x",
            "error": None,
        },
    )
    assert db.scalars(select(ItemLink)).first() is None


def test_deleting_a_sent_product_tells_the_connector(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    webhook(shop_client, "store.connected", connected(business))
    drain(settings, fake)
    deleted = shop_client.delete(f"/api/businesses/{business.id}/items/{item_id}", headers=headers)
    assert deleted.status_code in (200, 204), deleted.text
    assert [e.kind for e in pending(db)] == [outbox.ITEM_DELETE]
    drain(settings, fake)
    assert fake.calls("DELETE", rf"/products/{item_id}$")


def test_a_failing_push_is_retried_with_the_error_kept(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    add_item(shop_client, business, headers)
    webhook(shop_client, "store.connected", connected(business))
    fake.down = True
    assert drain(settings, fake) == 0
    entry = pending(db)[0]
    assert entry.attempts == 1 and entry.last_error
    assert entry.next_attempt_at > entry.created_at


def test_disconnecting_tells_the_connector_and_forgets_the_store(
    shop_client: TestClient,
    db: Session,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    webhook(shop_client, "store.connected", connected(business))
    r = shop_client.delete(f"/api/businesses/{business.id}/shopify", headers=headers)
    assert r.status_code == 200, r.text
    assert fake.calls("DELETE", rf"/v1/stores/{business.id}$")
    db.expire_all()
    assert db.scalars(select(StoreLink)).first() is None


def test_a_reserved_subdomain_is_refused_in_our_words(
    shop_client: TestClient,
    db: Session,
    fake: FakeConnector,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    webhook(shop_client, "store.connected", connected(business))
    fake.stores[str(business.id)] = connected(business)
    url = f"/api/businesses/{business.id}/shopify/subdomain"
    r = shop_client.post(url, headers=headers, json={"subdomain": "www"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "reserved_subdomain"
    ok = shop_client.post(url, headers=headers, json={"subdomain": "souk"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["subdomain_hostname"] == "souk.janoubona.net"
