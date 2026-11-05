# Janoubona Partner API (v1)

A read-only REST API over Janoubona's **approved stores** and their
**available products**, with each store's Shopify storefront and each
product's buy link. It exposes only data that is already public on
janoubona.net. It is built for partners who list or promote Janoubona's
catalogue, such as Yalla Pay and AdsTalk.

- **Base URL:** `https://www.janoubona.net/api/partner/v1`
- **Machine-readable spec:** [`partner-api-v1.openapi.json`](partner-api-v1.openapi.json)
  (OpenAPI 3.1), for Postman, Insomnia or client generators.

The spec is generated from the code by `backend/scripts/partner_openapi.py`,
and `backend/tests/test_partner_openapi.py` fails CI when the two differ. After
changing a partner route or field, run `python -m scripts.partner_openapi` in
`backend/` and update this page in the same pull request.

## Contents

1. [How to call it](#1-how-to-call-it)
2. [Conventions](#2-conventions)
3. [Authentication and scopes](#3-authentication-and-scopes)
4. [Pagination](#4-pagination)
5. [Incremental sync](#5-incremental-sync)
6. [Rate limits](#6-rate-limits)
7. [Errors](#7-errors)
8. [Endpoints](#8-endpoints)
9. [Object reference](#9-object-reference)
10. [Code samples](#10-code-samples)
11. [Data policy, versioning and support](#11-data-policy-versioning-and-support)

## 1. How to call it

Every call needs an API key in the `Authorization` header. Opening the base
URL in a browser therefore answers `401 bad_api_key`: a browser address bar
cannot send the header.

1. **Get a key.** A Janoubona manager issues one at
   `https://www.janoubona.net/admin/api-partners`. It starts with `jnb_`, and
   is shown **once**.
2. **Call a route.** Use any of the following.

**Terminal (curl):**

```bash
curl -H "Authorization: Bearer jnb_YOUR_KEY" \
  "https://www.janoubona.net/api/partner/v1/stores?connected=true"
```

**Hoppscotch** (https://hoppscotch.io, in the browser, nothing to install):

1. Choose method `GET`, URL `https://www.janoubona.net/api/partner/v1/stores?connected=true`.
2. On the **Authorization** tab, choose **Bearer Token** and paste the key.
3. Press **Send**.

**Postman or Insomnia:**

- Import `partner-api-v1.openapi.json`, then set the collection's bearer
  token to the key.
- Or make a `GET` request with **Authorization → Bearer Token**.

Never put a real key in this repository, a ticket or a chat: the repository is
public. Use `jnb_YOUR_KEY` in examples.

## 2. Conventions

| | |
|---|---|
| Base URL | `https://www.janoubona.net/api/partner/v1` (production). HTTPS only. |
| Format | JSON, UTF-8. Text is mostly Arabic. Store and product names come exactly as the shop wrote them. |
| Identifiers | `id` fields are UUIDs and never change. `slug` fields are URL names and may be Arabic: percent-encode them in URLs. |
| Timestamps | ISO 8601 with a timezone, in UTC, e.g. `2026-11-05T09:48:37.120000Z`. |
| Money | `price` is a decimal string, e.g. `"36.00"`, with an explicit `currency` (`USD` or `LBP`). Prices are never converted between currencies. `price` is `null` when the shop states none. |
| Media | Image paths are relative to `https://www.janoubona.net` (`/media/...`), and publicly readable. |
| Language | Error messages follow `Accept-Language`: Arabic by default, English with `Accept-Language: en`. Error `code`s never change with the language. |
| Tracing | Every response carries an `X-Request-ID` header. Quote it when asking about a request. |
| Unknown fields | Fields may be added within v1. Clients must ignore fields they do not know. |

## 3. Authentication and scopes

Send the key as a bearer token on every request:

```
Authorization: Bearer jnb_YOUR_KEY
```

- **Keys** start with `jnb_`, one per partner. A key is shown once, when it is
  issued. Janoubona stores only its SHA-256 hash and cannot read it back.
- **Keep keys server-side.** Never ship a key in a mobile app or a web page.
  Call the API from your backend.
- **Rotating** a key replaces the old one immediately. **Revoking** it stops
  it. Managers do both at `/admin/api-partners`.

| Scope | Grants |
|---|---|
| `stores:read` | `GET /stores`, `GET /stores/{slug}` |
| `products:read` | `GET /products` |

## 4. Pagination

List endpoints return a page, ordered by `(updated_at, id)` ascending and
paged by an opaque cursor. The cursor stays correct even when data changes
while you page through it.

```json
{ "items": [ ... ], "next_cursor": "MjAyNi0xMS0wNVQwOTo0ODozNy4xMjAwMDArMDA6MDB8..." }
```

- **`limit`:** 1–200, default 50.
- **`next_cursor`:** pass it back as `cursor`. It is `null` on the last page.
- **Cursors are opaque.** A changed or truncated cursor answers
  `422 bad_cursor`.

## 5. Incremental sync

1. **Initial load.** Record the current time `T0` (UTC), then page through
   `/stores` and `/products` to the end.
2. **Updates.** Every few minutes, record `T1`, then call each list with
   `updated_since=T0` and page to the end. Upsert each item by `id`, then set
   `T0 = T1`.
3. **Removals.** A store that stops being approved, or a product that stops
   being available, simply stops appearing in the lists.
   - Run a full load periodically, e.g. nightly, and remove what was not
     returned.
   - For a single store, `GET /stores/{slug}` answering `404` means hide it.

`updated_since` is inclusive (`updated_at >= updated_since`), so an item can
come back twice across runs. Upserting by `id` makes that harmless.

## 6. Rate limits

- **The limit:** each key may make **600 requests per hour** (a 3,600-second
  window).
- **Over the limit:** the API answers `429`, with a `Retry-After` header in
  seconds and the same value in `error.details.retry_after_seconds`. Wait that
  long, then continue.
- **Staying under it:** use `limit=200` to make fewer requests. The limit is
  set by `PARTNER_API_PER_KEY_LIMIT` and `PARTNER_API_PER_KEY_WINDOW_SECONDS`
  on the API.

## 7. Errors

Every error uses one envelope:

```json
{ "error": { "code": "bad_api_key", "message": "Missing or invalid API key.", "details": { } } }
```

| HTTP | `code` | Meaning |
|---|---|---|
| 401 | `bad_api_key` | The key is missing, wrong or revoked, or was not sent as `Bearer`. |
| 403 | `scope_missing` | The key lacks the scope this route needs. |
| 404 | `not_found` | No approved store has this slug. It may be suspended or renamed. |
| 422 | `bad_cursor` | The cursor was altered. Restart from the first page. |
| 422 | `validation_error` | A parameter is invalid, e.g. `limit=500` or a malformed `updated_since`. `details.fields` lists each problem. |
| 429 | `rate_limited` | Too many requests. Wait `Retry-After` seconds. |
| 500 | `internal_error` | A fault on our side. Retry with backoff, and quote the `X-Request-ID`. |

## 8. Endpoints

### `GET /stores` (scope `stores:read`)

Approved stores, oldest change first.

| Query parameter | Type | Description |
|---|---|---|
| `connected` | boolean, default `false` | `true`: only stores with a live, connected Shopify store. |
| `updated_since` | date-time | Only stores changed at or after this time. |
| `cursor` | string | `next_cursor` from the previous page. |
| `limit` | integer 1–200, default 50 | Page size. |

Responses: `200` `StorePage`, `401`, `403`, `422`, `429`.

### `GET /stores/{slug}` (scope `stores:read`)

One approved store. Responses: `200` `Store`, `401`, `403`, `404`, `429`.

```bash
curl -H "Authorization: Bearer jnb_YOUR_KEY" -H "Accept-Language: en" \
  "https://www.janoubona.net/api/partner/v1/stores/boutique-lilac"
```

The response is live data from Boutique Lilac, shortened with `...`:

```json
{
  "id": "d2d0402a-b347-4e32-bc89-f298d1fac4d3",
  "name": "بوتيك ليلاك",
  "slug": "boutique-lilac",
  "short_description": "يختص المتجر ببيع الملابس النسائية، الفولارات... (Ladies wear, Foulard)",
  "logo_url": "/media/businesses/d2d0402a-.../logo/39afb459....jpg",
  "cover_url": null,
  "phone": "+961...", "whatsapp": "+961...",
  "category": { "id": "ea667690-...", "name_ar": "ألبسة", "slug": "clothing", "icon": "shirt" },
  "custom_category_text": null,
  "location": { "id": "7c7e72de-...", "name_ar": "صريفا", "slug": "صريفا", "type": "TOWN", "parent_id": "e0e6a935-..." },
  "rating_average": null, "rating_count": 0,
  "goods_origin": "IMPORTED",
  "displaced_from": null,
  "created_at": "2026-11-04T15:11:17.982158Z",
  "page_url": "https://www.janoubona.net/business/boutique-lilac",
  "website": null,
  "latitude": 33.28124, "longitude": 35.39327,
  "updated_at": "2026-11-05T...Z",
  "shop_domain": "boutiquelilacc.myshopify.com",
  "online_store_url": "https://boutiquelilacc.janoubona.net",
  "subdomain_hostname": "boutiquelilacc.janoubona.net",
  "logo_thumb_url": null, "cover_thumb_url": null
}
```

### `GET /products` (scope `products:read`)

Available products of approved stores, oldest change first.

| Query parameter | Type | Description |
|---|---|---|
| `store` | string | Only this store's products (its slug). |
| `updated_since` | date-time | Only products changed at or after this time. |
| `cursor` | string | `next_cursor` from the previous page. |
| `limit` | integer 1–200, default 50 | Page size. |

Responses: `200` `ProductPage`, `401`, `403`, `422`, `429`.

```bash
curl -H "Authorization: Bearer jnb_YOUR_KEY" \
  "https://www.janoubona.net/api/partner/v1/products?store=boutique-lilac&limit=200"
```

```json
{
  "items": [{
    "id": "8b3b0547-cbbe-4649-913a-a61e179615d8",
    "slug": "طقم-لورين",
    "store_slug": "boutique-lilac",
    "title": "طقم لورين",
    "description": "يتميز ببلوزة بأكمام طويلة وياقة أنيقة...",
    "price": "36.00",
    "currency": "USD",
    "image_url": "/media/businesses/d2d0402a-.../item/232bf929....jpg",
    "images": [],
    "goods_origin": "IMPORTED",
    "page_url": "https://www.janoubona.net/product/طقم-لورين",
    "buy_url": "https://boutiquelilacc.janoubona.net/products/طقم-لورين",
    "updated_at": "2026-11-05T09:48:...Z"
  }],
  "next_cursor": null
}
```

## 9. Object reference

Fields marked **\*** are always present and never `null`.

### Store

| Field | Type | Description |
|---|---|---|
| `id`* | uuid | Stable identifier. |
| `name`* | string | Display name, as the shop wrote it. |
| `slug`* | string | URL name; used by `/stores/{slug}` and `/products?store=`. |
| `short_description` | string, null | One-line description. |
| `logo_url`, `cover_url` | string, null | Image paths, relative to the site. |
| `phone`, `whatsapp` | string, null | Public numbers, in E.164 format. `null` when the shop chose not to publish them. |
| `category` | Category, null | The main category. |
| `custom_category_text` | string, null | The shop's own wording, when it chose "Other". |
| `location` | Location, null | Town or district. |
| `rating_average` | number, null | Average of the published ratings (1–5). `null` until the store is rated. |
| `rating_count`* | integer | The number of published ratings. |
| `goods_origin`* | enum | `LOCAL` (made in the South) or `IMPORTED`. |
| `displaced_from` | string, null | Where the owner was displaced from, only when they chose to show it. |
| `created_at`*, `updated_at`* | date-time | Created, and last changed (UTC). |
| `page_url`* | string | The store's page on janoubona.net. |
| `website` | string, null | The shop's own website. |
| `latitude`, `longitude` | number, null | The map pin (WGS 84). |
| `shop_domain` | string, null | The connected Shopify store, e.g. `name.myshopify.com`. `null` if none. |
| `online_store_url` | string, null | Where to send buyers: the Shopify storefront, on its janoubona.net address when one is set. |
| `subdomain_hostname` | string, null | The store's `name.janoubona.net` address. |
| `logo_thumb_url`, `cover_thumb_url` | null | Reserved; always `null` in v1. |

### Product

| Field | Type | Description |
|---|---|---|
| `id`* | uuid | Stable identifier. |
| `slug`* | string | URL name. |
| `store_slug`* | string | The store it belongs to. |
| `title`* | string | Product name. |
| `description` | string, null | Plain text. |
| `price` | decimal string, null | The price in `currency`. `null` when not stated. |
| `currency`* | enum | `USD` or `LBP`. |
| `image_url` | string, null | The main photo. |
| `images`* | string[] | Additional photos. It may be empty. |
| `goods_origin`* | enum | `LOCAL` or `IMPORTED`. |
| `page_url`* | string | The product's page on janoubona.net. |
| `buy_url` | string, null | The product on the shop's Shopify store, where payment happens. `null` when the shop has no connected store, or the product is not there yet. |
| `updated_at`* | date-time | Last changed (UTC). |

### Category and Location

| Object | Fields |
|---|---|
| Category | `id`, `name_ar`, `slug`, `icon`, `sort_order`, `is_active`, plus counts. |
| Location | `id`, `name_ar`, `slug`, `type` (`GOVERNORATE`, `DISTRICT` or `TOWN`), `parent_id`, `sort_order`, `is_active`, plus counts. |

The count fields are not populated in this feed; do not rely on them.

## 10. Code samples

### Python: full or incremental sync

```python
import os, time, requests

BASE = "https://www.janoubona.net/api/partner/v1"
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {os.environ['JANOUBONA_KEY']}", "Accept-Language": "en"})

def walk(resource, **params):
    params.setdefault("limit", 200)
    while True:
        r = S.get(f"{BASE}/{resource}", params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", "60")))
            continue
        r.raise_for_status()
        page = r.json()
        yield from page["items"]
        if not page["next_cursor"]:
            return
        params["cursor"] = page["next_cursor"]

for store in walk("stores", connected="true"):
    print(store["name"], store["online_store_url"])
for product in walk("products", updated_since="2026-11-05T00:00:00Z"):
    print(product["title"], product["price"], product["currency"], product["buy_url"])
```

### Node.js (18+)

```js
const BASE = "https://www.janoubona.net/api/partner/v1";
const headers = { Authorization: `Bearer ${process.env.JANOUBONA_KEY}`, "Accept-Language": "en" };

async function* walk(resource, params = {}) {
  const q = new URLSearchParams({ limit: "200", ...params });
  for (;;) {
    const res = await fetch(`${BASE}/${resource}?${q}`, { headers });
    if (res.status === 429) {
      await new Promise((r) => setTimeout(r, 1000 * Number(res.headers.get("Retry-After") || 60)));
      continue;
    }
    if (!res.ok) throw new Error(`${res.status} ${(await res.json()).error?.code}`);
    const page = await res.json();
    yield* page.items;
    if (!page.next_cursor) return;
    q.set("cursor", page.next_cursor);
  }
}

for await (const p of walk("products", { store: "boutique-lilac" })) console.log(p.title, p.buy_url);
```

## 11. Data policy, versioning and support

- **Never in the feed:**
  - stores that are pending, rejected or suspended;
  - unavailable products;
  - any personal data of shop owners (identity, personal phone, documents);
  - orders or customer data.

  Everything returned is already public on janoubona.net.
  `backend/tests/test_partner_api.py` pins this.
- **Buying:** `buy_url` and `online_store_url` point to the shop's own Shopify
  store, where checkout and payment happen. Janoubona processes no payments.
- **Versioning:** v1 is stable.
  - Within v1, only fields, parameters or endpoints are added.
  - A breaking change comes as `/v2`, announced in advance. v1 keeps running
    while partners migrate.
- **Keys and support:** request a key, a scope or more capacity from the
  Janoubona team. Quote the `X-Request-ID` of any request you ask about.
