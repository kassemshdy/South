# Maintenance contract — verify-gate

## Must stay in step with

| This skill states | Authority |
|---|---|
| The three job groups and their commands | `.github/workflows/ci.yml` |
| Backend commands and the venv path | `AGENTS.md` § Command Execution Guide |
| The no-Arabic guard's scan roots | `backend/tests/test_i18n.py` |
| The `mcp` / `pydantic` version conflict | `mcp-server/requirements.txt`, `backend/requirements.txt` |
| The Chromium path | the installed `/opt/pw-browsers/` version |
| The approximate backend test count | the actual suite |
| `SEED_OWNER_PASSWORD` being what the e2e specs sign in with | `backend/scripts/seed.py`, `frontend/e2e/support/sign-in.ts` |

## What makes it wrong

- A new CI job, or a job renamed, without a matching step here. **A gate that
  passes locally and fails in CI is worse than no gate**, because it is
  trusted.
- A pinned tool version changing such that a command differs.
- The Chromium directory version changing — the path is version-numbered, so a
  browser upgrade silently breaks the Playwright line.
- A trap in `references/traps.md` that stops being true. Delete it; a stale
  warning teaches an agent to distrust the file.

## When to add to references/traps.md

Only for a failure that misleads: a step that fails for a reason other than
the code under test, or one that reports success without running. An ordinary
test failure is not a trap.
