# MCP server

An agent-facing view of the directory: **read all of it, write only to the
support ticket board.** Lives in [`mcp-server/`](../mcp-server), speaks MCP
over stdio, and is wired up by [`.mcp.json`](../.mcp.json) at the repo root.

## Why it is an HTTP client

The server holds no database connection and imports nothing from
`backend/app`. Every call it makes is a request to the API, which routes
through a FastAPI endpoint to a service to a repository — so it inherits the
rules the service layer enforces (an assignee must be an administrator, a
`sort_order` the server re-derives, a slug the server owns) and there is no
second path into the database that could drift from them.

Three consequences worth knowing:

- **It cannot bypass the disclosure boundary.** Repositories deliberately make
  no authorization decisions (`repositories/base.py`); the `*Out` schemas and
  `api/serializers.py` are what keep an account holder's identity off a public
  payload, and `tests/test_identity.py` pins that. Going through HTTP means
  those schemas apply to the agent too.
- **It needs no database credentials**, so no TCP proxy on the `postgres`
  service. That matters here: that service has no persistent volume, and a
  redeploy triggered by a config change wipes the whole database (see
  AGENTS.md).
- **It keeps its own virtualenv.** `mcp` requires `pydantic>=2.12` while the
  backend pins `pydantic==2.10.4`; a shared environment would silently
  upgrade the API's own validation library.

## Two transports

**stdio is the default, and the safe one.** The client is the process that
spawned the server, nothing listens on a port, and the credentials never leave
the machine. This is what `.mcp.json` uses and what Claude Code runs locally.

**HTTP is for a client that cannot spawn a process** — a claude.ai connector, a
scheduled routine on someone else's machine. It reaches further, so it costs
more:

```bash
SOUTH_MCP_TRANSPORT=http
SOUTH_MCP_TOKEN=<32+ chars>          # required; no token, no server
SOUTH_MCP_PUBLIC_URL=https://…       # the URL clients actually reach
```

`SOUTH_MCP_TOKEN` is not optional and there is no flag to make it optional.
What the HTTP transport exposes is the whole directory — **including listings
no visitor may see** — plus the power to write to the ticket board. So the
process exits 2 with a message rather than serving that to whoever finds the
URL. A token under 32 characters is refused for the same reason: a guessed
token is full read access.

`SOUTH_MCP_PUBLIC_URL` must be `https://` outside localhost. A bearer token
sent over plain HTTP is a token anyone on the path can copy.

Verified against a running server: no header → **401**, wrong token → **401**,
correct token → **200** and twelve tools, with `platform_stats` returning real
data. The `/.well-known/oauth-protected-resource` document stays public, as
the protocol requires.

### Two ways to present the same secret

**A bearer token**, compared with `hmac.compare_digest` so a `==` cannot leak
its length and then its content through timing. Enough for anything that can
send an `Authorization` header — Claude Code, a script, a routine.

**Or the OAuth flow**, for a client that speaks only OAuth. claude.ai's
connector setup begins with dynamic client registration and fails on a
bearer-only server — *"Couldn't register with South MCP's sign-in service"* is
what that looks like. So `south_mcp/oauth.py` implements the authorization
server: `/register`, `/authorize`, `/token`, `/revoke` and the metadata
documents.

**What it is not.** There is no per-user identity. The MCP signs in to the
directory as one administrator, so there is no second person for OAuth to
identify. The authorization step checks that whoever is connecting holds
`SOUTH_MCP_TOKEN`, via a consent page that asks for it. The security still
rests on that one secret; the OAuth machinery exists so a client that speaks
only OAuth can present it. **Do not read this as the directory having gained
real user authentication.**

Why the consent page is not skipped: having `authorize` redirect straight back
with a code would hand a token to anyone who can reach the endpoint — which is
the whole internet — and the shared secret would then protect nothing.

**State lives in memory.** Registered clients, codes and tokens are lost on
restart, so a redeploy of the service means re-authorising the connector. The
service rebuilds only when `mcp-server/**` changes, which is rare. Persisting
them would mean giving this service storage of its own, and storage holding
OAuth tokens is a bigger commitment than the problem currently justifies.

Verified end to end against a running server: registration 201, authorize 302
to the consent page, **wrong token 400**, right token 302 with a code and the
`state` echoed, token exchange 200 with access and refresh, **a replayed code
400**, the issued token accepted, the shared token still accepted, and a bogus
one 401.

## Configuration

| Variable | Meaning |
|---|---|
| `SOUTH_API_URL` | API base URL — `http://127.0.0.1:8000` locally, the `api-develop` host for staging, the live host for production |
| `SOUTH_AGENT_EMAIL` | Service-account email |
| `SOUTH_AGENT_PASSWORD` | Service-account password |

There are no defaults and no credentials in the repo. With any of them
missing the server exits with a message naming what is absent, rather than
starting and failing one tool call at a time — which from the far side of a
stdio pipe looks like a broken directory rather than a missing password.

The service account must have `role=ADMIN`: `feedback_tickets.reporter_id` is
non-nullable, and `FeedbackService._validate_assignee` rejects an assignee who
is not an administrator. Give the agent its own account rather than reusing a
person's, so the board shows who filed a ticket.

## Tools

Twelve. Read-only unless marked.

| Tool | Notes |
|---|---|
| `list_tickets` | Filters (status, priority, assignee, title) are applied client-side: the API returns the whole board in one response |
| `get_ticket` | Full ticket, comments, attachment *metadata* |
| `list_assignable_admins` | Who a ticket may be assigned to |
| `create_ticket` | **writes** — always lands at the bottom of `BACKLOG` |
| `update_ticket` | **writes** — fields and/or status; see below |
| `comment_on_ticket` | **writes** — append-only |
| `list_businesses` / `get_business` | Any status, including what no visitor can see |
| `list_talent` | Any status |
| `list_products` | Public catalogue only — see the gap below |
| `list_taxonomy` | Categories, locations, talent skills |
| `platform_stats` | Counts across the directory |

### `update_ticket` is one tool on purpose

The API cannot change a ticket's status through its edit route — only through
`POST /tickets/{id}/move`. And because no schema in the app sets
`extra="forbid"`, a `PUT` carrying a `status` **returns 200 with nothing
changed**:

```python
FeedbackTicketUpdateIn.model_validate({"status": "DONE", "priority": "HIGH"})
# -> fields set: {"priority": HIGH}
```

Two tools mirroring the two routes would let an agent report a move that never
happened. One tool that routes internally — `status` to `/move`, everything
else to the edit route — cannot. `backend/tests/test_feedback.py::
test_update_edits_fields_without_touching_status` pins the API side;
`mcp-server/tests/test_tools.py` pins the routing.

`github_issue_number` links a ticket to the roadmap issue serving it. Pass a
number to link, `0` to unlink — `None` already means "leave this field alone"
for every other argument, so it could not also mean "remove". The API rejects
anything below 1, since GitHub numbers issues from 1 and a 0 would arrive as a
card linking nowhere.

`resolved_at` is stamped and cleared by the server when a ticket enters and
leaves `DONE`. `index` is the position in the destination column; every other
card in both affected columns is renumbered server-side.

## What it deliberately cannot do

No tool approves, rejects, suspends or reactivates a listing, deletes
anything, or downloads a verification or CV document. Moderation decides
whether a real person's shop is visible, and those documents are scans of
identity papers. The credential can reach those endpoints; this process gives
a model no way to ask.

**Owner identity is redacted before it reaches a tool.** `AdminBusinessOut`
and `AdminTalentOut` carry an `owner_identity` block (legal name, birth year,
gender, marital status, place of civil registration, place of residence) plus
the owner's personal phone, because a human reviewer needs them. An agent
never does, so `south_mcp/redaction.py` strips them from every response at any
depth. What a shop *publishes* — its own `phone` and `whatsapp` — survives, the
same distinction `tests/test_observability.py` pins for error reports.

The reason for redacting rather than trusting the tool list: ticket text and
listing content are written by other people, so they are exactly the kind of
input that can talk a model into fetching something it should not. Data the
process never holds cannot be talked out of it.

## Known gaps

- **No admin product read.** Items are reachable only through the public
  catalogue (approved businesses, available items) or the owner-scoped
  `/api/my/businesses/{id}/items`, so a pending shop's products cannot be
  seen. Needs an admin endpoint.
- **No server-side ticket filtering.** `list_board()` returns every ticket
  with every relation eagerly loaded; the filters here run on the result.
- **Attachment bytes are not exposed.** A bug screenshot can show anything
  that was on the reporter's screen.

## Running a routine against it

The intended loop: read the board, take the top `TODO`, implement it, open a
pull request, comment the link on the ticket, move the ticket to
`IN_PROGRESS`. **Never to `DONE`** — `DONE` means shipped, and a person decides
that after a merge.

A routine that runs unattended needs its tool names pre-approved in
`.claude/settings.json`, or it will stall on a permission prompt with nobody
there to answer.
