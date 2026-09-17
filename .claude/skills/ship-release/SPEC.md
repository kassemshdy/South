# Maintenance contract — ship-release

## Must stay in step with

| This skill states | Authority |
|---|---|
| Which branch drives which services | `docs/RAILWAY.md`, `AGENTS.md` § Pull Requests / Deploys |
| The live and staging hostnames | the Railway API, **not** `docs/RAILWAY.md` |
| The `postgres` service having no volume | the Railway project |
| The stats endpoint used as the post-deploy proof | `backend/app/api/v1/businesses.py` |

## What makes it wrong

- **The hostnames drifting again.** `docs/RAILWAY.md` was wrong about them
  twice — first a live URL answering "Application not found", then a staging
  host that had been replaced — and is now correct: live `janoubona.net`,
  staging `janoubona-develop.up.railway.app`. The doc is worth reading again,
  which is why this skill now cites it. The Railway API stays the authority
  anyway: a hostname is configuration that can change without anyone touching
  this repository, so a doc can only ever be a cache of it. Two wrong entries
  is the evidence, not a reason to distrust the current ones.
- The `postgres` service gaining a persistent volume. That would remove the
  single most dangerous constraint in the release path, and the warning should
  then be rewritten rather than deleted, so the history stays legible.
- A migration appearing in a release. The pre-flight compares counts and
  treats equality as reassurance; it does not tell you what to do when they
  differ, on purpose — that is a judgement, and it belongs to a person.
