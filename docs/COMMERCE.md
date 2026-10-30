# Third-party commerce: Shopify stores, store subdomains, the partner feed

The investor's model (30 Oct 2026): **Janobona is the door, not the shop.**
Each business runs its own Shopify store, which it owns and pays for. Payment
and delivery happen there; Yalla Pay is a Shopify app the store installs. Janobona
pushes the shop's products to that store and sends visitors to it. Partners
(Yalla Pay, AdsTalk) read a feed of the stores and products.

Everything here does nothing until its variables are set, like every other
integration in this repository.

## Decisions (the owners', 30 Oct 2026)

| Question | Decision |
|---|---|
| Whose Shopify account | The shop owner's own; they connect it to Janobona through OAuth. |
| Sync direction | Janobona → Shopify only. Owners keep editing on Janobona. Two-way comes later. |
| Buying | Connected shops get "Buy online" links to Shopify. Every other shop keeps the order request and WhatsApp. |
| Payments | None in this codebase. Yalla Pay runs inside each Shopify store. |
| Domain | `janoubona.net`, on Cloudflare. |
| Partners | A read-only, key-protected feed: `docs/PARTNER_API.md`. |

## Getting a store

**Shopify has no public API that creates stores.** A store is made by the
merchant signing up, or by hand by a Partner in the Partner Dashboard, so
Janobona cannot open one for a shop automatically. What it does instead:

- An owner whose shop has no store sees "Create your Shopify store" on the
  products page, with three steps: sign up, add Yalla Pay, come back and
  connect.
- The button opens `SHOPIFY_SIGNUP_URL`. Set it to the Janobona Partner
  referral link (Partner Dashboard → Referrals), so Shopify credits the
  referral to Janobona. Unset, it is Shopify's public free-trial page.
- Creating stores on merchants' behalf would need a platform partnership
  with Shopify. That is a business conversation, possibly through the
  investor, not something code can do.

## Setting it up

1. **Shopify Partner account.** In it, create a **public app with unlisted
   distribution**.
   - Custom distribution only covers one merchant, so it is not enough for
     many independent stores.
   - App URL: `https://janoubona.net/dashboard`.
   - Allowed redirection URL: `https://janoubona.net/api/integrations/shopify/callback`.
   - Webhooks go to `https://janoubona.net/api/integrations/shopify/webhooks`. Subscribe to
     `app/uninstalled` and `shop/update`, and set the three mandatory
     compliance topics (`customers/data_request`, `customers/redact`,
     `shop/redact`) to the same URL.
   - Shopify's app review is needed before any store but a development store
     can install it, and it can take weeks.
2. **Variables on `api`.**
   - `SHOPIFY_API_KEY` and `SHOPIFY_API_SECRET` come from the app.
   - `INTEGRATION_ENCRYPTION_KEY` is a Fernet key. Generate it with the
     command in `backend/.env.example`. It is never the same as
     `SECRET_KEY`; production refuses to start if it is.
   - Optional: `SHOPIFY_API_VERSION` (pinned) and `SHOPIFY_SCOPES`.
3. **Cloudflare.**
   - Create an API token scoped to Zone → DNS → Edit on `janoubona.net`.
   - Set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID`.

## How it works

- **Connecting** (`app/services/shopify_connection.py`):
  - The owner types their `*.myshopify.com` address on the products page and
    approves the app in Shopify.
  - The callback is believed only with Shopify's HMAC, our signed `state` and
    the same shop.
  - The offline token is stored encrypted (`app/core/crypto.py`).
  - Only an **approved** listing can connect.
- **Pushing** (`app/services/outbox.py`, `app/services/shopify_sync.py`):
  - A session hook adds a row to `integration_outbox` in the same flush as
    any product change on a connected shop.
  - A worker in the API's lifespan sends it with `productSet`. The product
    is created once, then updated by id through `shopify_product_links`.
  - Nothing is sent when nothing Shopify sees has changed.
  - A product with no price, or priced in a currency the store does not
    sell in, is never pushed. The reason shows on the owner's card.
  - Failures retry with backoff up to 8 times.
- **Visitors** (`app/services/storefront.py`):
  - `online_store_url` on the shop page and `buy_url` on products are set only
    while the connection is live.
  - Uninstalling the app in Shopify removes them (`app/uninstalled` webhook).
- **Subdomains** (`app/services/store_subdomain.py`):
  - The owner picks a Latin name, because slugs keep Arabic script.
  - We create a **DNS-only** CNAME to `shops.myshopify.com`. Shopify issues
    the certificate and cannot do so behind Cloudflare's proxy.
  - Shopify's API cannot attach a domain to a store, so the owner does it
    once in Shopify (Settings → Domains → Connect existing domain).
  - The card shows that step until the store's primary domain is the
    subdomain.
- **Disconnecting / deleting:**
  - The token is revoked and the DNS record removed.
  - Products already in Shopify stay there: they are the owner's.

## What it does not do yet

- Shopify → Janobona: products edited in Shopify are not read back.
- Variants, stock, and orders or sales counts from Shopify.
- Suspending a listing does not set its Shopify products to draft. The
  Janobona links disappear, but the store is the owner's.
- Push webhooks to partners.
