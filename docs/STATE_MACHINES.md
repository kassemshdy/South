# State machines

Every status column in this app is a small state machine: a set of states and
the moves allowed between them. Where those moves are written as a table
(`app/services/moderation.py` `TRANSITIONS`), a person, a test and an agent
can read the rule in one place. Where they are scattered `if` statements, the
rule is implicit and drifts. This page keeps the audit of every such machine,
the decisions taken, and the prompt that started it, so the next session (or
person) starts from here rather than from zero.

## The prompt (the owners', 9 Nov 2026)

> Find all of the implicit state machines in my app. Make the best decision
> that will elevate all three: the user experience (UX), developer experience
> (DX), and agent experience (AX) always, without breaking anything.

Re-run it the same way: audit every status column and nullable "done"
timestamp, rank by risk, propose the smallest change that makes each rule
explicit, **show the plan before building** (the owners' rule), and file what
is not built now as issues.

## Decisions so far

- **Plan first, then small PRs.** The audit and plan were approved for later;
  each piece is a GitHub issue under the umbrella
  [#494](https://github.com/kassemshdy/South/issues/494):
  - [#495](https://github.com/kassemshdy/South/issues/495) Tickets: APPROVED
    only from NEEDS_APPROVAL (open question: everyone, or agents only).
  - [#496](https://github.com/kassemshdy/South/issues/496) Testimonials and
    stories: a repeated approve/reject does nothing (re-approving a story
    must not extend its 24 hours).
  - [#497](https://github.com/kassemshdy/South/issues/497) Shopify: resync a
    connected shop's products when it leaves or re-enters APPROVED.
  - [#498](https://github.com/kassemshdy/South/issues/498) Route
    registration, attach and conversion through the moderation table.
  - [#499](https://github.com/kassemshdy/South/issues/499) Orders, service
    requests, employer requests: write their allowed moves down.
- **A draft of the shared helper** (`app/core/state_machine.py`,
  `Transitions`) and the ticket guard is on branch `fix/state-machines`
  (commit 4aca62b), not merged.
- **Already changed since the audit (10 Nov 2026):**
  - Review needs at least one product and the owner's ID card
    (`BusinessService.missing_requirements`, `TalentService.missing_requirements`).
  - Staff can send a draft (or a rejected shop) to review on the owner's
    behalf: a new `ModerationService.send_to_review`, the same SUBMIT
    transition and audit row, without the owner's readiness list; approval
    keeps its logo rule.

## Rules for any new status

1. Declare the allowed moves next to the service that changes the status (a
   table, like `TRANSITIONS`), not in each route.
2. Refuse an illegal move with a `ConflictError` carrying a translation key,
   so the screen shows a sentence and an agent gets a stable `code`.
3. Make a repeated action a no-op rather than a second side effect.
4. Record who moved it and when, where a person will later ask.
5. Let the frontend ask the backend what is allowed rather than re-deriving
   the rule from the status.

## The audit (9 Nov 2026)

The full read-only audit, kept as it was written. Line numbers are as of that
day and drift.

## Implicit state machines in South, highest risk first

Paths are relative to `/home/user/South`. "No from-check" means the writer sets the new state without looking at the current one.

### 1. Business / Talent moderation (`BusinessStatus`, shared by both)
- **Where the state lives:** `backend/app/models/business.py:145-167` (`status`, `rejection_reason`, `submitted_at`, `approved_at`, `approved_by`, `outreach_*`) and `backend/app/models/talent.py:237-246`. The audit tables are `ModerationAction` (`business.py:431`) and `TalentModerationAction` (`talent.py:612`).
- **States:** DRAFT, PENDING_REVIEW, APPROVED, REJECTED, SUSPENDED.
- **Declared table:** `backend/app/services/moderation.py:28-34` has the one real transition table (`TRANSITIONS`). `backend/app/services/talent_moderation.py:42-91` reuses that table but copies the side-effect code (an intentional mirror, per its docstring).
- **Writers that skip the table (no from-check, no audit row, no `submitted_at`):**
  - `backend/app/services/registration.py:230` (business) and `:265` (talent): set PENDING_REVIEW directly after `create()` returns DRAFT.
  - `backend/app/api/v1/admin/applications.py:98,105` (`attach_discarded_application`): same. `BusinessService.create` commits inside itself (`backend/app/services/business.py:~95`), so a failure after that leaves an orphan DRAFT and the application stays un-dismissed. A retry then creates a duplicate.
  - `backend/app/services/talent_conversion.py:79-85`: copies `status`, `approved_at`, `approved_by` and `rejection_reason` onto a brand-new Business. This bypasses the logo-required rule that `ModerationService.approve` enforces (`moderation.py:119-127`). An APPROVED profile with no photo becomes an APPROVED shop with no logo. No ModerationAction row is written, so the shop's audit trail is empty.
- **Other risks:**
  - `approved_at` is never cleared on SUSPEND or REJECT. REACTIVATE only sets it when it is None. `growth_report.py:366-377` measures approval time from `created_at` to `approved_at`, so resubmissions and converted shops (whose copied `approved_at` predates their new `created_at`) skew the median.
  - Owners can edit an APPROVED listing with no return to review (`backend/app/api/v1/businesses.py:209-214`, `TalentService.update`).
  - A MANAGER using view-as can call the owner's `/submit`. The audit row then records the owner as `actor_id` (`backend/app/core/dependencies.py:84-123`), and the same manager can approve it.
  - Owner `is_active=False` is not considered by `public_query` (`backend/app/repositories/business.py:94-96`, `backend/app/repositories/talent.py:168-170`). A disabled owner's APPROVED listings stay public. No route disables an owner anyway: `is_active` is only written for staff (`backend/app/api/v1/admin/staff.py:97-100`).
- **Frontend mirror:**
  - Labels: `frontend/src/utils/format.ts:12-26` (`STATUS_KEYS`, `STATUS_TONES`) and `features/businesses/StatusBadge.tsx`.
  - Buttons per status: `pages/admin/AdminReviewPage.tsx:170-211` and `AdminTalentReviewPage.tsx:226-302`.
  - Owner side: `pages/dashboard/DashboardPage.tsx:265` (`canSubmit = DRAFT||REJECTED`, which duplicates the backend table) and `:298-363`.
  - Also `AdminBusinessesPage.tsx:254-267`, `ListingsMapCard.tsx:37-45`, `ShopViewsWhatsappButton.tsx:20`.
  - MCP: `mcp-server/south_mcp/server.py:47` has a `ListingStatus` literal. Moderation is read-only there.
- **Tests:** `backend/tests/test_moderation.py:223` (illegal transitions) and `test_talent.py` cover the service. No test checks the audit row or `submitted_at` on the registration or attach paths, or that conversion keeps the logo rule.

### 2. Shopify connector (StoreLink / ItemLink / IntegrationOutbox; free-form strings)
- **Where the state lives:** `backend/app/models/integration.py`.
  - `StoreLink.status` is a `String(20)` holding "PENDING|CONNECTED|UNINSTALLED". Only `CONNECTED` exists as a constant. Plus `connected_at` and `last_error`.
  - `ItemLink.state` holds "QUEUED|SYNCED|SKIPPED|FAILED", plus `active`, `synced_at`, `error`.
  - The outbox state is the combination of `done_at`, `attempts`, `next_attempt_at` and `last_error`.
- **Writers:**
  - `backend/app/services/connector.py:295-308` (`_record_store`) writes whatever status string the webhook sends. No from-check, no ordering or timestamp guard, so an older webhook can overwrite a newer state.
  - `connector.py:318-347` (`handle_event`): disconnect deletes the rows.
  - `connector.py:174-185` (`_record_item`).
  - `backend/app/services/outbox.py:184-201`. `done_at` means both "succeeded" and "gave up after 8 attempts" (`MAX_ATTEMPTS`, `outbox.py:40`); the only difference is a non-null `last_error`. `pending_pushes` (`backend/app/api/v1/integrations.py:96-100`) silently drops entries that were given up on.
- **Biggest risk:**
  - The outbox hook (`outbox.py:86-125`) watches only `BusinessItem` and `BusinessItemImage`. A shop's moderation status is checked only when a product is sent (`connector.py:169`, `available = is_available and APPROVED`). So when a connected shop is SUSPENDED, nothing re-sends its products and they stay buyable on Shopify.
  - `StoreLink` stays CONNECTED after suspension. `push_profile`/`sync_now` check only `is_live`, not the business status (`connector.py:253-265`); only `start` checks APPROVED (`:230`).
  - The admin Shopify picker lists APPROVED shops only (`integrations.py:139`), so a suspended shop's live store disappears from that page.
- **Two sources that can disagree:** the admin detail page reads the live connector status (`integrations.py:103-105`), while the picker reads the mirrored `StoreLink.status` (`:148`).
- **Frontend:** `features/integrations/ShopifyCard.tsx:259,283` and `pages/admin/AdminShopifyPage.tsx:115` hardcode the strings "CONNECTED" and "UNINSTALLED".
- **Tests:** `backend/tests/test_shopify.py` has no test for suspension.

### 3. Support tickets (`FeedbackStatus` board)
- **Where the state lives:** `backend/app/models/feedback.py:45` (`status`), `:76` (`resolved_at`), `github_issue_number`, `sort_order`.
- **States:** BACKLOG, TODO, IN_PROGRESS, NEEDS_FEEDBACK, NEEDS_APPROVAL, APPROVED, DONE.
- **Writer:** only `FeedbackService.move` (`backend/app/services/feedback.py:110-147`). It allows any column to any column, with no from-check. It does keep `resolved_at` consistent: set when entering DONE, cleared when leaving it. DONE→TODO is allowed and clears `resolved_at`.
- **Risks:**
  - APPROVED ("a person approved the release") can be reached from any column, by any SUPPORT or MANAGER, and by the MCP agent.
  - MCP `update_ticket` (`mcp-server/south_mcp/server.py:203-250`) does a PUT and then `/move` as two non-atomic calls. Its "do not move to DONE" rule exists only in the tool description text.
  - Moving to TODO or APPROVED fires the triage routine (`backend/app/services/triage_trigger.py:31`, `feedback.py:146`), so the agent can trigger itself.
  - The frontend shows approve/reject only at NEEDS_APPROVAL (`pages/admin/AdminFeedbackPage.tsx:570`), but the Telegram deep link (`?decision=approve`) runs `move(APPROVED)` (`:519`). The backend does not check the ticket is still at NEEDS_APPROVAL.
  - Reject is a comment followed by `move(TODO)`, also non-atomic (`:531-534`).
  - `FeedbackTicketUpdateIn` silently ignores `status`. The MCP server's docstring notes this (`server.py:13-17`).
- **Frontend mirror:** `utils/format.ts:28` (`FEEDBACK_STATUS_KEYS`), `AdminFeedbackPage.tsx:47,85-96` (column list duplicated twice).
- **Tests:** `backend/tests/test_feedback.py:121` (`resolved_at`), `:602`. Nothing tests restricting entry into APPROVED.

### 4. Testimonials (`TestimonialStatus`)
- **Where the state lives:** `backend/app/models/testimonial.py:66,71`.
- **States:** PENDING_REVIEW, PENDING_OWNER and HIDDEN (legacy, still allowed in the DB), APPROVED, REJECTED.
- **Writers:** `backend/app/services/testimonial.py:112-125`, with no from-check.
  - REJECTED→APPROVED is allowed, which contradicts the docstring in `backend/app/api/v1/testimonials.py:224-226` ("so the same text cannot be resubmitted and approved by accident").
  - Re-approving overwrites `approved_at`. Reject does not clear `approved_at`, and the repository sorts on it (`backend/app/repositories/testimonial.py:76`).
  - The rating is recomputed on each transition. Conversion re-points testimonials but copies the rating instead of recomputing it (`talent_conversion.py:113-117`).
- **Frontend:** `pages/admin/AdminTestimonialsPage.tsx:39,177,187` shows approve whenever status is not APPROVED, so the button appears on REJECTED and HIDDEN rows.

### 5. Stories (ad-hoc string status)
- **Where the state lives:** `backend/app/models/story.py:22-25,53-55`: string constants plus a CHECK constraint, `approved_at`, `expires_at`. Not an enum in `enums.py`.
- **Writers:** `backend/app/services/stories.py:163-176`, with no from-check.
  - Re-approving an APPROVED story resets `expires_at` to 24h from now, so its lifetime can be extended without limit.
  - REJECTED→APPROVED is allowed.
  - Expiry is implicit: an APPROVED story past `expires_at` is hard-deleted lazily (`:178-197`).
- **Frontend:** a third `STATUS_KEYS` map in `features/stories/StoryManager.tsx:18,151`; `pages/admin/AdminStoriesPage.tsx:112-139`.

### 6. Orders and service requests (`OrderStatus`, shared enum)
- **Where the state lives:** `backend/app/models/order.py:59`, `backend/app/models/service_request.py:66`. States: NEW, CONTACTED, DONE.
- **Writers:** `backend/app/services/order.py:111-114` and `backend/app/services/service_request.py:89-92` are identical `set_status` functions with no from-check and no timestamp. DONE→NEW is possible through the API.
- **Frontend:** only forward buttons, and the label maps are duplicated: `features/cart/OrderCard.tsx:10,94,99`, `features/talent/OwnerServiceRequests.tsx:16,123,133`.

### 7. Employer requests (`EmployerRequestStatus`)
- **Where the state lives:** `backend/app/models/talent.py:526`. States: NEW, CONTACTED, HIRED.
- **Writer:** `backend/app/services/employer_request.py:83-92`, same pattern: no from-check, HIRED→NEW allowed, no timestamp or actor.
- **Frontend:** `pages/admin/AdminEmployerRequestsPage.tsx:19,183`.

### 8. Job openings (`JobStatus` + `is_published` + `deadline`)
- **Where the state lives:** `backend/app/models/job.py:62,84,87`. The state is two independent dimensions (published × ACTIVE/FILLED/UNAVAILABLE) plus a status derived from the deadline.
- **Two ways to derive the status:** `effective_status` (`backend/app/api/v1/jobs.py:73-85`) treats an ACTIVE job past its deadline as UNAVAILABLE without storing that. Admins see `saved_status` and the effective status side by side (`jobs.py:306-307`).
- **Writers:**
  - Admin PUT: any status, `status_changed_at` updated (`jobs.py:360-366`).
  - publish/unpublish: unconditional (`:373-387`).
  - Public submission creates an unpublished job without setting `status_changed_at` (`:257-266`).
- **Frontend:** `features/jobs/JobCard.tsx:16,85`, `pages/admin/AdminJobOpeningsPage.tsx`.

### 9. Partner requests, open service requests, discarded applications (nullable timestamps)
- **Partner requests:** `solved_at` (`backend/app/models/partner.py:36`). Solve/reopen in `backend/app/api/v1/partners.py:90-121`.
- **Open service requests:** `solved_at` (`backend/app/models/open_service_request.py:41`). Solve/reopen in `backend/app/api/v1/open_service_requests.py:110-137`.
- Both are idempotent `is None` checks with near-identical copied route code and no actor recorded.
- **Discarded applications:** `dismissed_at` (`backend/app/models/application.py:54`) means both "dismissed" and "attached" (`backend/app/api/v1/admin/applications.py:65,108`). There is no reopen, and no way to tell which of the two happened.

### 10. Users (credentials and access)
- **Where the state lives:** `backend/app/models/user.py`:
  - `password_hash` NULL means an applicant who cannot sign in yet.
  - `must_change_password` (`:117`) is never set to True any more. Only `backend/app/services/auth.py:213,229` write it (always False), so the guard in `backend/app/core/dependencies.py:180` is dead code.
  - `token_version` (`:121`) is bumped in `auth.py:214,231` and `admin/staff.py:100`.
  - `is_active`, `role`, `staff_role`.
- **Risks:**
  - Changing `staff_role` does not bump `token_version` (`staff.py:95-96`). This is harmless because the role is read live.
  - The last-manager guard exists (`staff.py:86-94`).
- **View-as:** the state lives only in JWT claims (`va`, `atv`) and is re-validated on every request (`dependencies.py:84-123`). This is sound.
- **Dead column:** `TalentProfile.last_confirmed_at` (`backend/app/models/talent.py:233`) is written nowhere.

### 11. Publish flags (low risk)
All are plain toggles with no from-check:
- Articles: `is_published` + `published_at` set once (`backend/app/api/v1/admin/articles.py:118-129`).
- Workshops: `backend/app/api/v1/workshops.py:283,293`.
- Reels: `backend/app/api/v1/reels.py:114`.
- Activities: "public" means `is_archived=False` AND `image_url` IS NOT NULL (`backend/app/api/v1/activities.py:61`), so removing the photo unpublishes the activity. Registration is open while `registration_mode=ON_SITE` and the activity has not ended (`:153`).
- Item availability: `BusinessItem.is_available`, combined with business APPROVED and `image_url` (`backend/app/repositories/item.py:68-75`).
- Outreach: `outreach_contacted_at` with `_by` and `_note` (`backend/app/api/v1/admin/businesses.py:114-131`). It is a toggle independent of moderation status.

## Patterns shared across machines
- **One status enum for two moderated entities:** `BusinessStatus` and `ModerationActionType` cover both businesses and talent. The table is shared, but the side-effect code is copied into two services. The `submitted_at`/`approved_at`/`rejection_reason` triple is duplicated as well.
- **"Moderation-like" machines with no table:** testimonials, stories and the feedback APPROVED column each have their own approve/reject with no from-check. There are three separate status label maps on the frontend (`format.ts`, `StoryManager.tsx`, `AdminTestimonialsPage.tsx`).
- **The same enum for two contact logs:** `OrderStatus` is used for orders and service requests, `EmployerRequestStatus` is parallel to it, and all three `set_status` functions are identical and unconstrained.
- **Nullable timestamp used as a boolean:** `solved_at` (×2), `dismissed_at`, `outreach_contacted_at`, `resolved_at`, outbox `done_at`. Each has idempotent `is None` checks copied per route, and none records an actor (except `outreach_contacted_by`).
- **"Visible to the public" is computed in several places:** `public_query` (status only), `item.public_query` (status + availability + photo), `connector.product_payload`, `storefront.buy_url` and `_id_verified` (`backend/app/api/serializers.py:348`). None of them consider the owner's `is_active`.
- **The frontend re-derives allowed actions itself** (`canSubmit`, the approve/reject button conditions) instead of getting them from the backend, so it can drift from `TRANSITIONS`.
