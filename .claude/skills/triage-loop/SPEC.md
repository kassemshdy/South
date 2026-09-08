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
- **A `DONE` transition creeping in.** The prohibition is the whole reason a
  human still reviews these passes; if a future version of this file lets an
  agent close its own ticket, the board stops meaning anything.
- **The step-0 refusal being softened.** An unconfigured pass that "does
  something useful anyway" is the failure mode this skill exists to prevent:
  it invents work, and invented work is indistinguishable from a real ticket
  once it is a PR.

## Deliberately not automated

Moderation (approving or suspending a listing), merging, and moving a ticket
to `DONE`. Each decides something about a real person's livelihood or about
what the project has shipped. The MCP server has no tool for the first, and
this skill forbids the other two.
