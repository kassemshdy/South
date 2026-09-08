# Maintenance contract — ship-release

## Must stay in step with

| This skill states | Authority |
|---|---|
| Which branch drives which services | `docs/RAILWAY.md`, `AGENTS.md` § Pull Requests / Deploys |
| The live and staging hostnames | the Railway API, **not** `docs/RAILWAY.md` |
| The `postgres` service having no volume | the Railway project |
| The stats endpoint used as the post-deploy proof | `backend/app/api/v1/businesses.py` |

## What makes it wrong

- **`docs/RAILWAY.md` line 3 is known stale** — it records a live URL that
  returns "Application not found", and never recorded the staging host at all.
  This skill says to read the hosts from the Railway API for that reason. If
  the doc is ever fixed, simplify this skill; until then, do not trust it.
- The `postgres` service gaining a persistent volume. That would remove the
  single most dangerous constraint in the release path, and the warning should
  then be rewritten rather than deleted, so the history stays legible.
- A migration appearing in a release. The pre-flight compares counts and
  treats equality as reassurance; it does not tell you what to do when they
  differ, on purpose — that is a judgement, and it belongs to a person.
