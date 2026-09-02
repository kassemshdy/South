# Architecture

## Shape of the system

```
   Browser (Arabic RTL SPA)
        │  fetch /api/*
        ▼
┌────────────────────────────────────────────┐
│  FastAPI                                    │
│  ┌──────────────────────────────────────┐  │
│  │ api/      routing, serialization     │  │
│  ├──────────────────────────────────────┤  │
│  │ services/ business rules             │  │
│  ├──────────────────────────────────────┤  │
│  │ repositories/  data access           │  │
│  ├──────────────────────────────────────┤  │
│  │ models/   SQLAlchemy                 │  │
│  └──────────────────────────────────────┘  │
│     auth/otp        storage/                │
│     (protocol)      (protocol)              │
└────────┬───────────────────┬────────────────┘
         ▼                   ▼
   PostgreSQL 16      Disk or S3-compatible
```

In production the same FastAPI process also serves the built SPA, so there is
one deployable unit.

## Layering rules

Dependencies point one way: **api → services → repositories → models**.

- **api/** — parses input, calls one service, serializes the result. No SQL, no
  business rules. Authorization is expressed as dependencies
  (`CurrentUser`, `AdminUser`, `OwnedBusiness`).
- **services/** — the rules: what makes a listing complete enough to submit,
  which status transitions are legal, how the search haystack is derived.
  Owns transaction boundaries (`commit`).
- **repositories/** — the only code that builds queries. Makes no authorization
  decisions, so the same method is safely reusable from owner and admin paths.
- **schemas/** — Pydantic DTOs. ORM objects never cross the API boundary.

`api/serializers.py` is the single place that converts models to responses,
which is what keeps the privacy rules (below) auditable.

## Decisions worth knowing

**Synchronous SQLAlchemy.** FastAPI runs `def` endpoints in a threadpool. For
this workload that is comfortably fast and avoids the sharp edges of async
sessions for whoever maintains this next.

**Public visibility has exactly one gate.**
`BusinessRepository.public_query()` is the only definition of "what a visitor
may see" (`status == APPROVED`). Every public endpoint and the sitemap build on
it, and a test asserts that no non-approved listing escapes through any of them.

**Ownership is checked by loading, not by trusting.** The
`require_owned_business` dependency loads the row and compares `owner_id` to the
JWT subject. Someone else's id returns **404, not 403**, so the API does not
confirm that an id exists to a user with no claim to it. Administrators are
deliberately *not* granted owner powers: they act through the admin API, which
records an audit trail.

**Moderation is a table, not scattered `if`s.** `services/moderation.py` holds
one map from action to (allowed source statuses → resulting status). Every
transition writes a `ModerationAction` row. Adding moderation of *edits* to an
approved listing later means adding entries there, not rewriting endpoints.

**Arabic search is normalized on both sides.** Arabic spelling varies in
everyday use — أحمد/احمد, حلويّات/حلويات, بلدة/بلده. `core/arabic.py` strips
diacritics and folds alef, teh-marbuta, alef-maqsura and hamza variants. The
normalized text is stored denormalized in `businesses.search_text` at write
time and applied to the query at read time, with a `pg_trgm` GIN index serving
substring matches. Item titles are folded into the same haystack, so searching
"زعتر" finds the bakery that sells it.

**Slugs keep their script.** "مناقيش الضيعة" becomes `مناقيش-الضيعة`, not the
vowel-less transliteration `mnqysh-ldy`, which is meaningless to an Arabic
reader and useless for Arabic search. Latin names still produce Latin slugs.
Slugs are generated once at creation and never change on rename, so shared links
keep working.

**Uploads are re-encoded, never passed through.** `services/images.py` decodes
every upload with Pillow (the declared content type is a hint, not evidence),
rejects anything that is not JPEG/PNG/WEBP, then resizes and re-encodes. That
strips EXIF — including GPS coordinates a shop owner did not intend to publish —
and bounds stored size. Only metadata goes in PostgreSQL.

**Prices are decimal strings end to end.** `Numeric(12,2)` in PostgreSQL,
serialized as strings in JSON, formatted only for display. No float rounding
touches money.

## Privacy rules

Phone numbers are personal data, and this application handles two distinct kinds:

| Field | Who can see it |
|---|---|
| `User.phone_number` (login) | The user themselves (`/api/me`) and administrators |
| `Business.phone` / `whatsapp` (published) | Everyone — the owner chose to publish these |

The two are never conflated. `BusinessDetailOut` — the public payload — has no
owner fields and no moderation state; `AdminBusinessOut` adds them. A test
asserts the public payload never contains `owner_phone`, `owner_id`, `status`,
`rejection_reason` or `search_text`.

## Authentication

Owners authenticate by phone and a one-time code; administrators by email and
password. Both produce the same JWT (HS256) carrying `sub`, `role` and `tv`
(token version). Bumping `User.token_version` invalidates every token previously
issued to that user.

OTP codes are stored only as bcrypt hashes, expire in five minutes, are
single-use, and allow five verification attempts. Requesting a code is rate
limited to three per phone per fifteen minutes and ten per IP per hour, counted
in the database so the limits hold across multiple workers.

## SEO

A single-page app serves one `index.html`, so a crawler or a WhatsApp link
preview fetching `/business/<slug>` would otherwise see generic tags. When the
API serves the built SPA it rewrites the head for business URLs
(`core/seo.py`) with the real name, description and image. The client-side
`useSeo` hook keeps tags correct during in-app navigation. `/sitemap.xml` lists
approved businesses only.

## Error handling and logging

Every failure leaves the API in one envelope:

```json
{ "error": { "code": "...", "message": "...", "details": { } } }
```

`message` is Arabic and safe to show a user; `code` is stable for the frontend
to branch on. Domain failures are typed exceptions (`NotFoundError`,
`ConflictError`, `RateLimitedError`, …) mapped by handlers in `main.py`.
Unexpected exceptions are logged with a traceback and reported as a generic
500 — never swallowed, never leaked.

Logs are single-line JSON with a per-request id (`X-Request-Id`, honoured from
the incoming header so a proxy can correlate).

## Frontend

Strict TypeScript with no `any`. One `apiClient` handles auth headers, the error
envelope and network failures; one `endpoints.ts` defines every call. Components
never call `fetch` directly. Server state is TanStack Query keyed through a
central `queryKeys` registry; forms are React Hook Form + Zod.

RTL is done with CSS logical properties (`ms-`/`me-`/`ps-`/`pe-`/`text-start`)
plus Radix's `DirectionProvider`, not by right-aligning text — which is what
makes adding an English locale later a configuration change rather than a
restyle. Latin runs inside Arabic text (prices, phone numbers, URLs) are
isolated with a `.ltr-nums` utility so bidirectional reordering does not mangle
them.

The public pages ship in the main bundle; the owner dashboard and admin area are
lazily loaded, because most visitors never sign in and should not pay to
download screens they will not open.

## Extension points

| Want to… | Change |
|---|---|
| Use a different SMS/WhatsApp gateway | Add an `OtpProvider` in `app/auth/otp/`, register in `factory.py` |
| Store images elsewhere | Add a `StorageBackend` in `app/storage/` |
| Moderate edits to approved listings | Extend the transition table in `services/moderation.py` |
| Replace search with OpenSearch | Reimplement `BusinessRepository.search_public`; the API contract is unchanged |
| Add English | Extract strings; the layout already uses logical properties |
