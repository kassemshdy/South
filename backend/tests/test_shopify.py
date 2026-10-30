"""A shop's own Shopify store: connecting it, pushing products, buy links.

Every call to Shopify and Cloudflare goes to an ``httpx.MockTransport``, so
nothing here touches the network. What is pinned:

- the routes do not exist until the integration is configured;
- the OAuth callback is believed only with Shopify's signature, our signed
  state and a matching shop, and the token is stored encrypted;
- a product edit on a connected shop queues exactly one push, in the same
  transaction -- and on any other shop, nothing;
- a push creates the product once, then updates it, and sends nothing when
  nothing Shopify sees has changed; a price in the wrong currency is never
  pushed;
- a buy link is public only while the connection is live;
- subdomains are DNS-only CNAMEs, and reserved names are refused.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from collections.abc import Callable, Iterator
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.integrations import get_http_client
from app.core.config import Settings, get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.database.session import SessionLocal
from app.main import create_app
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, ShopifyConnectionStatus
from app.models.integration import IntegrationOutbox, ShopifyConnection, ShopifyProductLink
from app.models.taxonomy import Category, Location
from app.services import outbox
from app.services.shopify_sync import make_handlers
from tests.conftest import post_item, sign_in
from tests.samples import ar

OWNER_PHONE = "03880001"
OTHER_PHONE = "03880002"
SHOP = "souk-test.myshopify.com"
SECRET = "shpss_test_secret"


def shopify_settings(**overrides: object) -> Settings:
    return get_settings().model_copy(
        update={
            "shopify_api_key": "test-api-key",
            "shopify_api_secret": SECRET,
            "integration_encryption_key": Fernet.generate_key().decode(),
            # The worker never runs on its own in a test; drain_once does.
            "integration_outbox_poll_seconds": 3600,
            "public_base_url": "https://janobona.test",
            **overrides,
        }
    )


class FakeShopify:
    """Records every request and answers like Shopify and Cloudflare would."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.currency = "USD"
        self.products = 0

    def graphql_calls(self) -> list[str]:
        return [
            json.loads(r.content)["query"]
            for r in self.requests
            if r.url.path.endswith("/graphql.json")
        ]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/admin/oauth/access_token":
            return httpx.Response(200, json={"access_token": "shpat_plain", "scope": "x"})
        if path == "/admin/api_permissions/current.json":
            return httpx.Response(200, json={})
        if request.url.host == "api.cloudflare.com":
            if request.method == "POST":
                return httpx.Response(200, json={"success": True, "result": {"id": "rec1"}})
            return httpx.Response(200, json={"success": True})
        query = json.loads(request.content)["query"]
        if "shop {" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "shop": {
                            "currencyCode": self.currency,
                            "primaryDomain": {"host": "souk.example.com"},
                        }
                    }
                },
            )
        if "productSet" in query:
            self.products += 1
            return httpx.Response(
                200,
                json={
                    "data": {
                        "productSet": {
                            "product": {
                                "id": "gid://shopify/Product/1",
                                "handle": "zaatar",
                                "status": json.loads(request.content)["variables"]["input"][
                                    "status"
                                ],
                                "variants": {"nodes": [{"id": "gid://shopify/ProductVariant/1"}]},
                            },
                            "userErrors": [],
                        }
                    }
                },
            )
        if "publications" in query:
            return httpx.Response(
                200,
                json={"data": {"publications": {"nodes": [{"id": "pub1", "name": "Online Store"}]}}},
            )
        if "publishablePublish" in query:
            return httpx.Response(200, json={"data": {"publishablePublish": {"userErrors": []}}})
        if "productDelete" in query:
            return httpx.Response(
                200, json={"data": {"productDelete": {"deletedProductId": "x", "userErrors": []}}}
            )
        return httpx.Response(400, json={"errors": [{"message": "unexpected"}]})


@pytest.fixture
def fake() -> FakeShopify:
    return FakeShopify()


@pytest.fixture
def settings() -> Settings:
    return shopify_settings()


@pytest.fixture
def shop_client(settings: Settings, fake: FakeShopify) -> Iterator[TestClient]:
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


def signed(params: dict[str, str], secret: str = SECRET) -> dict[str, str]:
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return {**params, "hmac": hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()}


def connect(client: TestClient, business: Business, headers: dict[str, str]) -> None:
    started = client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": "souk-test"}
    )
    assert started.status_code == 200, started.text
    state = parse_qs(urlparse(started.json()["authorize_url"]).query)["state"][0]
    back = client.get(
        "/api/integrations/shopify/callback",
        params=signed({"code": "abc", "shop": SHOP, "state": state, "timestamp": "1"}),
        follow_redirects=False,
    )
    assert back.status_code == 307, back.text
    assert back.headers["location"].endswith("shopify=connected")


def drain(settings: Settings, fake: FakeShopify) -> int:
    with httpx.Client(transport=httpx.MockTransport(fake)) as http:
        return outbox.drain_once(SessionLocal, make_handlers(settings, http))


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
    assert client.get("/api/integrations/shopify/callback").status_code == 404
    assert client.post("/api/integrations/shopify/webhooks", content=b"{}").status_code == 404


def test_production_refuses_a_half_configured_integration() -> None:
    hardened = get_settings().model_copy(
        update={"app_env": "production", "secret_key": "s" * 40, "admin_password": "Strong!pass1"}
    )
    with pytest.raises(RuntimeError, match="SHOPIFY_API_KEY"):
        hardened.model_copy(update={"shopify_api_key": "k"}).enforce_production_safety()
    with pytest.raises(RuntimeError, match="must differ"):
        hardened.model_copy(
            update={"integration_encryption_key": "s" * 40}
        ).enforce_production_safety()


def test_a_shop_without_a_store_is_offered_the_sign_up_link(
    db: Session, fake: FakeShopify, category: Category, location: Location
) -> None:
    """Shopify has no API that creates stores; the owner signs up themselves."""
    referral = "https://shopify.pxf.io/janobona"
    for client in _client_with(shopify_settings(shopify_signup_url=referral), fake):
        headers = sign_in(client, OWNER_PHONE)
        business = approved_business(client, db, headers, category, location)
        status = client.get(f"/api/businesses/{business.id}/shopify", headers=headers).json()
        assert status["connected"] is False
        assert status["signup_url"] == referral


# --- Connecting ----------------------------------------------------------------


def test_install_refuses_a_listing_that_is_not_approved(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    business.status = BusinessStatus.PENDING_REVIEW
    db.commit()
    response = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": SHOP}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "shopify_not_approved"


@pytest.mark.parametrize("shop", ["evil.com", "x.myshopify.com.evil.com", "https://a b"])
def test_install_refuses_anything_but_a_myshopify_address(
    shop_client: TestClient, db: Session, category: Category, location: Location, shop: str
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    response = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": shop}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "shopify_bad_shop"


def test_another_owner_cannot_reach_the_connection(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    other = sign_in(shop_client, OTHER_PHONE)
    assert (
        shop_client.post(
            f"/api/businesses/{business.id}/shopify/install", headers=other, json={"shop": SHOP}
        ).status_code
        == 404
    )


def test_a_callback_without_shopifys_signature_connects_nothing(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    started = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": SHOP}
    )
    state = parse_qs(urlparse(started.json()["authorize_url"]).query)["state"][0]
    forged = signed({"code": "abc", "shop": SHOP, "state": state}, secret="not-the-secret")
    back = shop_client.get(
        "/api/integrations/shopify/callback", params=forged, follow_redirects=False
    )
    assert back.headers["location"].endswith("shopify=shopify_bad_hmac")
    assert db.scalars(select(ShopifyConnection)).first() is None


def test_a_callback_for_a_different_shop_than_was_asked_is_refused(
    shop_client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    started = shop_client.post(
        f"/api/businesses/{business.id}/shopify/install", headers=headers, json={"shop": SHOP}
    )
    state = parse_qs(urlparse(started.json()["authorize_url"]).query)["state"][0]
    back = shop_client.get(
        "/api/integrations/shopify/callback",
        params=signed({"code": "abc", "shop": "other.myshopify.com", "state": state}),
        follow_redirects=False,
    )
    assert back.headers["location"].endswith("shopify=shopify_shop_mismatch")
    assert db.scalars(select(ShopifyConnection)).first() is None


def test_connecting_stores_the_token_encrypted_and_queues_every_product(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    add_item(shop_client, business, headers)
    add_item(shop_client, business, headers)
    assert pending(db) == []  # nothing queued before the store is connected

    connect(shop_client, business, headers)

    connection = db.scalars(select(ShopifyConnection)).one()
    assert connection.access_token_enc != "shpat_plain"
    assert "shpat_plain" not in connection.access_token_enc
    assert decrypt_secret(settings, connection.access_token_enc) == "shpat_plain"
    assert connection.primary_domain == "souk.example.com"
    assert connection.currency == "USD"
    assert len(pending(db)) == 2

    status = shop_client.get(f"/api/businesses/{business.id}/shopify", headers=headers).json()
    assert status["connected"] is True
    assert status["storefront_url"] == "https://souk.example.com"
    assert "access_token" not in json.dumps(status)


# --- Queueing and pushing --------------------------------------------------------


def test_an_edit_on_a_connected_shop_queues_one_push_and_others_queue_nothing(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    connect(shop_client, business, headers)
    drain(settings, fake)
    assert pending(db) == []

    edited = shop_client.put(
        f"/api/businesses/{business.id}/items/{item_id}",
        headers=headers,
        json={"price": "6.00"},
    )
    assert edited.status_code == 200, edited.text
    queued = pending(db)
    assert [(e.kind, e.payload["item_id"]) for e in queued] == [(outbox.ITEM_UPSERT, item_id)]

    # A shop with no store: edits queue nothing at all.
    other_headers = sign_in(shop_client, OTHER_PHONE)
    other = approved_business(shop_client, db, other_headers, category, location)
    add_item(shop_client, other, other_headers)
    assert len(pending(db)) == 1


def test_a_push_creates_once_then_updates_and_skips_what_did_not_change(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    connect(shop_client, business, headers)

    assert drain(settings, fake) == 1
    link = db.scalars(select(ShopifyProductLink)).one()
    assert link.shopify_product_id == "gid://shopify/Product/1"
    first = [q for q in fake.graphql_calls() if "productSet" in q]
    assert len(first) == 1
    assert any("publishablePublish" in q for q in fake.graphql_calls())
    sent = json.loads(
        next(r for r in fake.requests if b"productSet" in r.content).content
    )["variables"]["input"]
    assert "id" not in sent
    assert sent["variants"][0]["price"] == "4.50"
    assert sent["status"] == "ACTIVE"
    assert sent["files"][0]["originalSource"].startswith("https://janobona.test/")

    # The same product again: nothing Shopify sees changed, nothing is sent.
    shop_client.post(f"/api/businesses/{business.id}/shopify/sync", headers=headers)
    drain(settings, fake)
    assert len([q for q in fake.graphql_calls() if "productSet" in q]) == 1

    # A price change updates the same product, by its id.
    shop_client.put(
        f"/api/businesses/{business.id}/items/{item_id}", headers=headers, json={"price": "7.25"}
    )
    drain(settings, fake)
    update = json.loads(
        [r for r in fake.requests if b"productSet" in r.content][-1].content
    )["variables"]["input"]
    assert update["id"] == "gid://shopify/Product/1"
    assert update["variants"][0]["price"] == "7.25"


def test_a_product_in_another_currency_is_never_pushed(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    add_item(shop_client, business, headers, currency="LBP")
    connect(shop_client, business, headers)
    drain(settings, fake)
    assert fake.products == 0
    db.expire_all()
    connection = db.scalars(select(ShopifyConnection)).one()
    assert connection.last_error is not None and "LBP" in connection.last_error


def test_deleting_a_pushed_product_deletes_it_from_the_store(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    connect(shop_client, business, headers)
    drain(settings, fake)
    deleted = shop_client.delete(f"/api/businesses/{business.id}/items/{item_id}", headers=headers)
    assert deleted.status_code in (200, 204), deleted.text
    assert [e.kind for e in pending(db)] == [outbox.ITEM_DELETE]
    drain(settings, fake)
    assert any("productDelete" in q for q in fake.graphql_calls())


def test_a_failing_push_is_retried_later_with_the_error_kept(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    add_item(shop_client, business, headers)
    connect(shop_client, business, headers)

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    with httpx.Client(transport=httpx.MockTransport(down)) as http:
        assert outbox.drain_once(SessionLocal, make_handlers(settings, http)) == 0
    entry = pending(db)[0]
    assert entry.attempts == 1
    assert entry.last_error
    assert entry.next_attempt_at > entry.created_at
    assert db.scalars(select(ShopifyConnection)).one().last_error


# --- What visitors see ------------------------------------------------------------


def test_buy_links_are_public_only_while_the_store_is_connected(
    shop_client: TestClient,
    db: Session,
    settings: Settings,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    item_id = add_item(shop_client, business, headers)
    connect(shop_client, business, headers)
    drain(settings, fake)

    page = shop_client.get(f"/api/businesses/{business.slug}").json()
    assert page["online_store_url"] == "https://souk.example.com"
    item = db.get(BusinessItem, uuid.UUID(item_id))
    assert item is not None
    product = shop_client.get(f"/api/items/{item.slug}").json()
    assert product["buy_url"] == "https://souk.example.com/products/zaatar"
    assert "souk-test.myshopify.com" not in json.dumps(page)

    body = json.dumps({"id": 1}).encode()
    digest = base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()
    hook = shop_client.post(
        "/api/integrations/shopify/webhooks",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": digest,
            "X-Shopify-Topic": "app/uninstalled",
            "X-Shopify-Shop-Domain": SHOP,
        },
    )
    assert hook.status_code == 200
    db.expire_all()
    assert db.scalars(select(ShopifyConnection)).one().status is ShopifyConnectionStatus.UNINSTALLED
    assert shop_client.get(f"/api/businesses/{business.slug}").json()["online_store_url"] is None
    assert shop_client.get(f"/api/items/{item.slug}").json()["buy_url"] is None


def test_a_webhook_without_shopifys_signature_is_refused(
    shop_client: TestClient,
    db: Session,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    connect(shop_client, business, headers)
    hook = shop_client.post(
        "/api/integrations/shopify/webhooks",
        content=b"{}",
        headers={
            "X-Shopify-Hmac-Sha256": "forged",
            "X-Shopify-Topic": "app/uninstalled",
            "X-Shopify-Shop-Domain": SHOP,
        },
    )
    assert hook.status_code == 401
    db.expire_all()
    assert db.scalars(select(ShopifyConnection)).one().is_live


def test_disconnecting_revokes_the_token_and_forgets_the_store(
    shop_client: TestClient,
    db: Session,
    fake: FakeShopify,
    category: Category,
    location: Location,
) -> None:
    headers = sign_in(shop_client, OWNER_PHONE)
    business = approved_business(shop_client, db, headers, category, location)
    connect(shop_client, business, headers)
    response = shop_client.delete(f"/api/businesses/{business.id}/shopify", headers=headers)
    assert response.status_code == 200, response.text
    assert any(r.url.path == "/admin/api_permissions/current.json" for r in fake.requests)
    db.expire_all()
    assert db.scalars(select(ShopifyConnection)).first() is None


# --- <sub>.janoubona.net --------------------------------------------------------------


@pytest.fixture
def dns_settings() -> Settings:
    return shopify_settings(cloudflare_api_token="cf-token", cloudflare_zone_id="zone1")


@pytest.mark.parametrize(
    ("subdomain", "code"),
    [("www", "reserved_subdomain"), ("Bad_Name", "bad_subdomain"), ("-x", "bad_subdomain")],
)
def test_a_subdomain_must_be_a_free_latin_name(
    dns_settings: Settings,
    fake: FakeShopify,
    db: Session,
    category: Category,
    location: Location,
    subdomain: str,
    code: str,
) -> None:
    for client in _client_with(dns_settings, fake):
        headers = sign_in(client, OWNER_PHONE)
        business = approved_business(client, db, headers, category, location)
        connect(client, business, headers)
        response = client.post(
            f"/api/businesses/{business.id}/shopify/subdomain",
            headers=headers,
            json={"subdomain": subdomain},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == code


def test_a_subdomain_is_a_dns_only_cname_to_shopify(
    dns_settings: Settings,
    fake: FakeShopify,
    db: Session,
    category: Category,
    location: Location,
) -> None:
    for client in _client_with(dns_settings, fake):
        headers = sign_in(client, OWNER_PHONE)
        business = approved_business(client, db, headers, category, location)
        connect(client, business, headers)
        response = client.post(
            f"/api/businesses/{business.id}/shopify/subdomain",
            headers=headers,
            json={"subdomain": "souk"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["subdomain_hostname"] == "souk.janoubona.net"
        created = next(r for r in fake.requests if r.url.host == "api.cloudflare.com")
        assert json.loads(created.content) == {
            "type": "CNAME",
            "name": "souk.janoubona.net",
            "content": "shops.myshopify.com",
            "proxied": False,
            "ttl": 1,
        }


def _client_with(settings: Settings, fake: Callable[[httpx.Request], httpx.Response]) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings

    def http() -> Iterator[httpx.Client]:
        with httpx.Client(transport=httpx.MockTransport(fake)) as client:
            yield client

    app.dependency_overrides[get_http_client] = http
    try:
        with TestClient(app) as client:
            yield client
    finally:
        outbox.uninstall_hooks(SessionLocal)


def test_the_cipher_round_trips_and_refuses_another_key(settings: Settings) -> None:
    from app.core.crypto import CredentialCipherError

    secret = encrypt_secret(settings, "shpat_x")
    assert decrypt_secret(settings, secret) == "shpat_x"
    other = settings.model_copy(update={"integration_encryption_key": Fernet.generate_key().decode()})
    with pytest.raises(CredentialCipherError):
        decrypt_secret(other, secret)
