# Database

PostgreSQL 16. UUID primary keys throughout (nothing user-facing is guessable
or countable), `timestamptz` stored in UTC, and Alembic for every schema change.

## Entity relationships

```
              ┌──────────┐
              │  users   │
              └────┬─────┘
                   │ 1
                   │            owner_id
                   │ N
              ┌────▼──────────────────────────────┐
   category_id│           businesses               │location_id
  ┌───────────┤  status, slug, search_text, …      ├────────────┐
  │           └──┬──────────┬──────────┬───────────┘            │
  │              │1         │1         │1                       │
  │              │N         │N         │N                       │
┌─▼────────┐ ┌───▼──────┐ ┌─▼───────┐ ┌▼──────────────────┐  ┌──▼────────┐
│categories│ │ business │ │business │ │business_social_   │  │ locations │
│          │ │ _images  │ │ _items  │ │links              │  │ (tree)    │
└──────────┘ └──────────┘ └─────────┘ └───────────────────┘  └───────────┘
                   │1
                   │N
            ┌──────▼─────────────┐        ┌───────────────┐  ┌──────────────────┐
            │ moderation_actions │                           │rate_limit_events │
            │ (append-only)      │                           └──────────────────┘
            └────────────────────┘
```

## Tables

### `users`
One row per account. Owners have a phone and no password; administrators have
an email and a bcrypt password hash and no phone. Keeping both here makes
authorization a single `role` check.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `phone_number` | varchar(20) | unique, nullable — E.164, e.g. `+9613123456` |
| `email` | varchar(255) | unique, nullable — administrators |
| `password_hash` | varchar(255) | nullable — administrators only (bcrypt) |
| `display_name` | varchar(120) | nullable |
| `role` | enum | `OWNER` \| `ADMIN` |
| `is_active` | bool | disables sign-in |
| `token_version` | int | bump to revoke every issued JWT |

### `businesses`
The central table. `status` drives public visibility; `search_text` is the
Arabic-normalized haystack maintained by the service layer on every write.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `owner_id` | uuid | → `users`, cascade delete |
| `category_id` / `location_id` | uuid | → `categories` / `locations`, `SET NULL` |
| `name` | varchar(160) | |
| `slug` | varchar(180) | unique — the public URL, script-preserving |
| `short_description` | varchar(300) | shown on cards and in search results |
| `description` | text | |
| `phone` / `whatsapp` | varchar(20) | **published** contact, distinct from the login phone |
| `email` / `website` | | optional, validated |
| `logo_url` / `cover_url` (+ `_storage_key`) | varchar(500) | denormalized for fast card rendering |
| `address_text` | varchar(400) | |
| `latitude` / `longitude` | numeric(9,6) | optional |
| `maps_url` | varchar(1000) | optional |
| `status` | enum | `DRAFT` \| `PENDING_REVIEW` \| `APPROVED` \| `REJECTED` \| `SUSPENDED` |
| `rejection_reason` | text | shown to the owner; cleared on resubmission |
| `submitted_at` / `approved_at` | timestamptz | |
| `approved_by` | uuid | → `users` |
| `search_text` | text | normalized name + descriptions + address + category + location + item titles |

### `categories`, `locations`
Both administrator-managed, never hardcoded in the frontend. `locations` is a
self-referencing tree — governorate → district → town — via `parent_id`;
filtering by a district automatically includes its towns.

### `business_images`
Image **metadata** only; bytes live in the storage backend. `kind` is
`LOGO` \| `COVER` \| `GALLERY` \| `ITEM`; gallery order is `sort_order`.

### `business_items`
Products, services or menu items — one model, three presentations.
`price numeric(12,2)` nullable (some services are "price on request"),
`currency` is `USD` \| `LBP`, and `is_available` lets an owner hide a line
without deleting it.

### `business_social_links`
One row per platform per business, unique on `(business_id, platform)`. URLs are
validated against that platform's own hosts before storage.

### `moderation_actions`
Append-only audit trail. Each row records the action, the statuses it moved
between, who did it, and any reason. `admin_id` is null for owner-initiated
submissions; `actor_id` always identifies the person.

### `rate_limit_events`
One row per rate-limited action (`bucket`, `identifier`, `created_at`). Backing
the limiter with the database rather than process memory means limits hold when
the API runs several workers or replicas.

## Indexes

Beyond the primary and unique keys:

| Index | Serves |
|---|---|
| `ix_businesses_status_created_at` | the public directory, newest first |
| `ix_businesses_status_approved_at` | "recently approved" on the homepage |
| `ix_businesses_slug` | profile lookups |
| `ix_businesses_category_id`, `ix_businesses_location_id` | filters |
| `ix_businesses_search_text_trgm` (GIN, `gin_trgm_ops`) | Arabic substring search |
| `ix_business_items_title_trgm` (GIN) | matching a product name to its shop |
| `ix_business_items_business_sort` | ordered item lists |
| `ix_business_images_business_kind_sort` | gallery rendering |
| `ix_rate_limit_events_lookup` | auth throttling and the anonymous write limits |

`pg_trgm` is created by the initial migration.

## Deletion behaviour

Deleting a business cascades to its images, items, social links and moderation
actions. Deleting a user cascades to their businesses. Deleting a category or
location sets the reference to null rather than removing listings — and the
admin API refuses to delete either while it is still in use, offering
deactivation instead.

## Migrations

```bash
cd backend
alembic upgrade head                          # apply
alembic revision --autogenerate -m "message"  # create after changing models
alembic downgrade -1                          # roll back one step
```

Always review autogenerated migrations: Alembic does not detect every change,
and raw SQL (such as the trigram indexes) must be written by hand. Migrations
run automatically when the container starts, so a deploy never serves against an
old schema.

## Seed data

`python -m scripts.seed` is idempotent; `--reset` wipes first. It creates 15
categories, the South Lebanon location tree (both governorates, their districts
and sample towns), 16 businesses spread across every moderation status with
products and generated placeholder images, and the administrator account from
`ADMIN_EMAIL` / `ADMIN_PASSWORD`. Sample data is refused when
`APP_ENV=production`; `--admin-only` bootstraps just the administrator and is
permitted there.
