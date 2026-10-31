# Maintenance contract — triage-loop

## Must stay in step with

| This skill states | Authority |
|---|---|
| The MCP tool names and their arguments | `mcp-server/south_mcp/server.py`, `docs/MCP.md` |
| The three environment variables | `mcp-server/south_mcp/config.py` |
| Ticket statuses and priorities | `backend/app/models/enums.py` |
| The gate, and the branch/PR conventions | the `verify-gate` and `steward` skills |
| The rules a hurried pass breaks | `AGENTS.md` § Security Musts, § No Arabic |

## What makes it wrong

- A renamed or removed MCP tool. The pass would fail at the first call, which
  is the safe direction, but the skill should not name a tool that is gone.
- **A release of anything not `APPROVED` creeping in**: a merge into
  `master-claude` while develop carries a commit no approved ticket owns
  would put unapproved work live. Step 0.5's commit check is the guard.
- **A `DONE` transition creeping in.** The prohibition is the whole reason a
  human still reviews these passes; if a future version of this file lets an
  agent close its own ticket, the board stops meaning anything.
- **The step-0 refusal being softened.** An unconfigured pass that "does
  something useful anyway" is the failure mode this skill exists to prevent:
  it invents work, and invented work is indistinguishable from a real ticket
  once it is a PR.

## Deliberately not automated

Moderation (approving or suspending a listing), and deciding that a fix may
go live -- the routine releases only tickets a person moved to `APPROVED`
(the owners' decision, 31 Oct 2026, with the «اعتمِد» button on the Telegram
message), and moves them to `DONE` only after the live check. Each decides something about
a real person's livelihood or about what the project has shipped. The MCP
server has no tool for the first, and this skill forbids the other two.
Merging a green pull request into `develop-claude` is allowed since 31 Oct
2026 (the owners' decision), because develop is the preview a person approves
from, not the live site.
