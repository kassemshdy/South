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
- **No link between a ticket and a GitHub issue.** Nothing joins the board to
  the roadmap, so a routine cannot tell which issue serves which ticket
  without matching on title text. A nullable `github_issue_number` on
  `feedback_tickets` would close this.
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
