# Third-party commerce: Shopify stores, store addresses, the partner feed

The investor's model (30 Oct 2026): **Janoubona is the door, not the shop.**
Each business runs its own Shopify store, which it owns. Payment and delivery
happen there: Yalla Pay is a Shopify app the store installs. Partners (Yalla
Pay, AdsTalk) read a feed of the stores and products.

## Two services

```
Janoubona ──REST──▶ Shopify Connector ──▶ Shopify / Cloudflare
Janoubona ◀─signed webhooks── Shopify Connector ◀── Shopify
```

**Shopify Connector** (repository `kassemshdy/shopify-connector`) is shared
by every website that sells this way. It holds:
- the one Shopify app and every store's token, encrypted;
- each website's Cloudflare zone;
- the product sync to Shopify.

Its README and `docs/API.md` are the reference for any website joining.

**Janoubona** is one of the connector's websites ("tenants"). It holds no
Shopify or Cloudflare credential. It does four things:
- asks the connector for an authorize URL when an owner presses Connect;
- sends each product through the outbox: a session hook queues it in the
  same transaction as the edit, and a worker sends it;
- mirrors what the connector reports, through signed webhooks: the store
  goes in `store_links`, each product's buy link in `item_links`;
- shows "Visit the online store" and "Buy online" from that mirror.

## Decisions (the owners', 30–31 Oct 2026)

| Question | Decision |
|---|---|
| Whose Shopify account | The shop owner's own. The connector installs the shared app on it through OAuth. |
| Shopify app | **One shared app** for all websites: one Shopify review, and one connector. |
| Sync direction | Janoubona → Shopify only, for now. |
| Buying | Connected shops get "Buy online" links. Every other shop keeps the order request and WhatsApp. |
| Payments | None in either codebase. Yalla Pay runs inside each Shopify store. |
| Store addresses | `<name>.janoubona.net`, a DNS-only CNAME in Janoubona's Cloudflare zone, created by the connector. A shop's own domain also works. |
| Partners | A read-only, key-protected feed served by Janoubona: `docs/PARTNER_API.md`. |

## Getting a store

**Shopify has no public API that creates stores.** A store is made by the
merchant signing up, or by hand by a Partner. Janoubona therefore shows shops
without a store a "Create your Shopify store" button. It points to the
website's sign-up link held in the connector, for example the Partner
referral link.

## Setting it up

1. **In the connector**, register Janoubona once, and keep the API key and
   webhook secret it prints:
   ```bash
   python -m scripts.tenant create --slug janoubona --name Janoubona \
     --origin https://janoubona.net \
     --webhook-url https://janoubona.net/api/integrations/connector/webhooks \
     --subdomain-base janoubona.net
   ```
   Then `set --cloudflare-zone … --cloudflare-token …` for store addresses,
   and `set --signup-url …` for the sign-up button.
2. **On Janoubona's `api` service**, set `CONNECTOR_URL`, `CONNECTOR_API_KEY`
   and `CONNECTOR_WEBHOOK_SECRET`.
3. **The Shopify app's URLs** point to the connector, not to Janoubona. The
   connector's README has the exact values.

All three Janoubona variables unset means no Connect button, and every
Shopify route answers 404.

## How it behaves

- **Connecting:** only an approved listing can connect. The owner returns to
  `/dashboard/businesses/<id>/items?shopify=connected` (or an error code). The
  connector then sends `store.connected`, and Janoubona queues every product.
- **Products:**
  - What is sent is what a visitor would see: title, description, price and
    currency, public https photo addresses, and availability. A suspended
    listing's products are sent as not available.
  - The connector never converts a price. A product in another currency is
    reported as skipped, with the reason.
- **Buy links:** public only while the mirror says the store is connected.
  An uninstall in Shopify reaches Janoubona as `store.updated`, and the links
  disappear.
- **Disconnecting or deleting:**
  - Janoubona tells the connector, which revokes the token and removes the
    DNS record.
  - Products already in Shopify stay: they are the owner's.
- **Webhooks from the connector:** believed only with its signature,
  `X-Connector-Signature: t=…,v1=HMAC-SHA256(secret, "t." + body)`, at most 5
  minutes old.

## What it does not do yet

- Shopify → Janoubona: products edited in Shopify are not read back.
- Variants, stock, and orders or sales counts from Shopify.
- Push webhooks to partners.
