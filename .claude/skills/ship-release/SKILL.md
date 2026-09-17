---
name: ship-release
description: Promote develop-claude to master-claude (production) safely — the pre-flight checks that establish a release will not lose data, and the post-deploy verification against the real live host. Use when asked to merge to live, ship to production, release, or promote staging.
license: Apache-2.0
---

# Promoting staging to production

`master-claude` drives the live `api` and `web` services. `develop-claude`
drives `api-develop` and `web-develop`. A release is a PR from
`develop-claude` into `master-claude`.

## Pre-flight — establish it is safe, do not assume

1. **Compare Alembic migration counts on both branches.**

   ```bash
   git ls-tree -r origin/develop-claude --name-only backend/alembic/versions | wc -l
   git ls-tree -r origin/master-claude  --name-only backend/alembic/versions | wc -l
   ```

   Equal counts mean the schema does not move, which is the single most
   reassuring fact about a release here. A new migration is not a blocker, but
   it changes the risk and must be called out.

2. **Check nothing exists on production that is not on staging.**

   ```bash
   git log --oneline --no-merges origin/develop-claude..origin/master-claude
   ```

   Output here means production carries real commits staging does not — stop
   and ask before merging.

   **`--no-merges` is load-bearing, not tidying.** A release is a merge of
   `develop-claude` into `master-claude`, and that merge commit exists only on
   master — so without the flag this check reports every release ever made and
   always tells you to stop. It listed four such commits the last time it ran,
   one per release, and the list only grows. A check that always says "stop"
   is a check people learn to wave through, which is worse than not having it:
   the one time production really does carry a hotfix that never reached
   staging, it will look exactly like the noise. With the flag it comes back
   empty, so anything it prints is worth reading.

3. **Read the actual diff**, at least `--stat`, and say how large it is.

4. **Never trigger a `postgres` redeploy.** That service has no persistent
   volume; a redeploy wipes the whole database, schema included. Do not set a
   variable or change config on it as part of a release.

5. Run the `verify-gate` skill on the merge base if anything is in doubt.

## After the deploy

Verify against the **real live host**. `docs/RAILWAY.md` records them --
live is `janoubona.net` (a custom domain; `janoubona.up.railway.app` also
answers), staging is `janoubona-develop.up.railway.app` -- but that line has
carried a host returning "Application not found" twice now, so one check is
worth it: if a probe 404s, read the current domains from the Railway API
(`list-domains` on the `web` and `web-develop` services) rather than
concluding the deploy failed. Dead hosts not to reintroduce:
`web-production-b8196` and `web-develop-production-bce3`.

Check, and report the actual numbers:

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://<host>/
curl -s https://<host>/api/businesses/stats
```

The stats endpoint is the useful one: non-zero counts prove the database
survived the deploy. Also confirm a string the release introduced is present
in the served bundle, and one it removed is absent — the frontend is compiled,
so a stale bundle is otherwise invisible.

A browser cannot reach external hosts through this session's proxy
(`ERR_CONNECTION_RESET`), so do not claim a visual check. `curl` works.
