---
name: steward
description: Repo-specific conventions for driving a pull request on this repository to a mergeable state — which branch to base on, which CI jobs must pass, how to handle a red check or a review comment, and what never to do. Use when opening, watching, babysitting, autofixing, or iterating on a PR here.
license: Apache-2.0
---

# Driving a PR on this repo

## Branches

- Feature work branches from **`origin/develop-claude`** and targets it.
- `master-claude` is **production** — it auto-deploys the live `api` and `web`
  services. Only `develop-claude` is promoted to it, never a feature branch.
- **Base a new branch on `origin/develop-claude`, not on whatever is checked
  out.** Branching off another feature branch silently pulls that branch's
  commits into the new PR, so one slice's PR contains another's diff:
  `git fetch origin develop-claude && git checkout -B <name> origin/develop-claude`.
- Never rebase, amend, or force-push a branch someone else may have checked
  out; a merge commit keeps their working copy valid.

## What must be green

Four CI jobs (`.github/workflows/ci.yml`), plus a bot comment summarising
them:

| Job | Covers |
|---|---|
| Backend (pytest, ruff, mypy) | ~400 tests against a real Postgres, including the no-Arabic guard |
| Frontend (tsc, build) | Typecheck and production build |
| MCP server (pytest, ruff, mypy) | `mcp-server/`, no database or credentials needed |
| E2E (Playwright) | The acceptance suite on mobile Chromium, against a migrated and seeded stack; uploads `e2e-results` (screenshots, traces, server logs) on failure |

A push to `develop-claude` or `master-claude` runs the same workflow again, so
a release PR can show each job twice for one commit. Read the pair; a green
one does not stand in for a running one.

Railway also deploys a preview environment per PR and edits one status comment
repeatedly as the four services build. Those edits are noise — an all-green
Railway table is not CI, and a red one is not a CI failure.

## Before pushing

Run the fast checks from the `verify-gate` skill — ruff, mypy, `tsc -b` and
the no-Arabic guard, which take seconds. The full suites are CI's to run, not
the session's (issue #121): CI runs them on every PR and nothing merges red.

## State to action

Read the PR's current head every time — CI, mergeability, open threads — and
act on the first row that matches.

| State | Action |
|---|---|
| Merge conflict | Merge the base branch in and resolve. Never rebase or force-push a branch someone may have checked out. |
| A CI job failed | Root-cause and fix. See below. |
| A CI job still running | Wait. Meanwhile read any review threads. |
| Only a human approval is outstanding | Report and stop. Approval is not yours to give. |
| No checks after a few minutes | Report that no checks registered rather than assuming green. |
| All four jobs green, no threads, mergeable | Say it is ready to merge, and stop. |

**Actionable** here means the four CI jobs. The Railway preview comment is
not a check: it edits itself repeatedly as four services build, an all-green
table is not CI, and a red one is not a CI failure.

## When a job fails

Fix the cause, not the symptom. Read the whole log, trace from the error to
the source, and for an E2E failure open the `e2e-results` artifact — the
failure screenshot and trace usually name the cause outright. Reproduce
locally only when the log and artifacts cannot explain it.

Two rules with teeth:

- **After the same failure twice, stop and ask** rather than trying a third
  variation. Two identical failures mean the diagnosis is wrong, and further
  attempts spend CI time to confirm it.
- **"Flake" is not a root cause.** On this repo a failing acceptance
  assertion is a stale database far more often than a flake — reset and
  re-run, do not re-run alone. Never skip, disable, or relax a test to reach
  green; never push an empty commit or close and reopen a PR to kick CI.

A no-Arabic guard failure is usually a *comment*, not a string — including a
comment written to explain a translation key.

## When a review comment arrives

Small and local (a nit, a rename, a bot finding, an added test): implement,
verify, push, and resolve the thread. A review bot's finding is a bug report —
verify it and fix it rather than deferring it as design feedback.

Larger asks (multi-file refactors, API or schema changes, open-ended design
questions) on a PR you did not open: reply with a proposal and let the author
decide.

## Repo rules that outrank convenience

These come from `AGENTS.md` and are not negotiable to make a check pass:

- **Never commit a secret.** `SECRET_KEY`, `ADMIN_PASSWORD`, Twilio
  credentials and the admin bootstrap password are Railway variables — not
  literals in code, docs, tests, or a commit message.
- **Never touch the `postgres` service.** It has no persistent volume, so any
  redeploy — including one triggered by changing only its environment
  variables — wipes the entire database. Confirm with the user first.
- **Public endpoints return only `APPROVED` businesses**, and no public schema
  carries an account holder's identity. A failure in
  `backend/tests/test_identity.py` is a disclosure bug, not a stale assertion.
- **A `VITE_` variable is a build argument, not a runtime one.** Adding one
  means editing `backend/Dockerfile` *and* `frontend/Dockerfile`, and it needs
  a rebuild rather than a restart. Setting it only in the Railway dashboard
  does nothing.

## PR description

Say what changed and why, name the verification actually performed, and be
explicit about anything you could not check. State a measured result as a
measurement, not as an impression.
