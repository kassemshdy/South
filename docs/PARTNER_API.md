# Janobona partner API (v1)

A read-only feed of Janobona's approved stores and their available products,
for partners such as Yalla Pay and AdsTalk. It carries nothing a visitor to
the site could not already read. In addition, it gives the address of each
store's own Shopify store, where payment and delivery happen.

## Authentication

A Janobona manager issues each partner a key at `/admin/api-partners`. The key
is shown once. Send it as a bearer token:

```
Authorization: Bearer jnb_...
```

- **Errors:** a missing, wrong or revoked key answers `401`. A key without the
  scope a route needs answers `403`.
- **Scopes:** `stores:read` and `products:read`.
- **Rate limit:** 600 requests an hour per key by default. Over the limit
  answers `429` with `Retry-After`.

## Paging

Lists are ordered by `(updated_at, id)` and paged by cursor:

- `limit`: 1–200, default 50.
- `next_cursor`: pass it back as `cursor`. It is `null` on the last page.
- `updated_since`: an ISO 8601 timestamp. It returns only what changed since
  then, which is how to keep a copy in step.

## Routes

### `GET /api/partner/v1/stores`

Query parameters: `connected=true` (only stores with a live Shopify store),
`updated_since`, `cursor`, `limit`.

```json
{
  "items": [
    {
      "id": "…",
      "slug": "…",
      "name": "…",
      "short_description": "…",
      "logo_url": "/media/…",
      "cover_url": "/media/…",
      "phone": "…",
      "whatsapp": "…",
      "category": {"slug": "…", "name_ar": "…"},
      "location": {"slug": "…", "name_ar": "…"},
      "rating_average": 4.5,
      "rating_count": 12,
      "goods_origin": "LOCAL",
      "page_url": "https://janobona.com/business/…",
      "website": null,
      "latitude": 33.27,
      "longitude": 35.2,
      "updated_at": "2026-10-30T10:00:00Z",
      "shop_domain": "souk.myshopify.com",
      "online_store_url": "https://souk.janobona.com",
      "subdomain_hostname": "souk.janobona.com"
    }
  ],
  "next_cursor": null
}
```

Notes on the fields:

- `phone` and `whatsapp` are `null` when the owner chose not to publish them.
- `shop_domain`, `online_store_url` and `subdomain_hostname` are `null` for a
  store with no connected Shopify store.

### `GET /api/partner/v1/stores/{slug}`

Returns one store, in the same shape. It answers `404` for a listing that is not
approved.

### `GET /api/partner/v1/products`

Query parameters: `store` (a store's slug), `updated_since`, `cursor`, `limit`.

```json
{
  "items": [
    {
      "id": "…",
      "slug": "…",
      "store_slug": "…",
      "title": "…",
      "description": "…",
      "price": "4.50",
      "currency": "USD",
      "image_url": "/media/…",
      "images": ["/media/…"],
      "goods_origin": "LOCAL",
      "page_url": "https://janobona.com/product/…",
      "buy_url": "https://souk.janobona.com/products/zaatar",
      "updated_at": "2026-10-30T10:00:00Z"
    }
  ],
  "next_cursor": null
}
```

Notes on the fields:

- `price` is a decimal string.
- `buy_url` is the product's page on the shop's Shopify store. It is `null`
  when the shop has none, or when the product has not been sent there.
- Image paths are relative to `https://janobona.com`.

## What is never in the feed

The feed never includes:

- listings that are pending, rejected or suspended;
- unavailable products;
- the account holder's identity, personal phone or documents;
- orders.

`backend/tests/test_partner_api.py` pins this.
