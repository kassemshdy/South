# Review policy

What a review of this repository looks for, in order. Findings are reported
with a tier; a reviewer's attention belongs at the top of the list.

## Blocking — a finding here stops the merge

These are the boundaries `AGENTS.md` calls musts, each with a test that pins
it. Treat a failure as a defect in the change, never as a stale assertion.

1. **Secret exposure.** A credential as a literal in code, a doc, a test, a
   commit message, or a PR body. `SECRET_KEY`, `ADMIN_PASSWORD`, Twilio
   credentials and the admin bootstrap password are Railway variables only.
2. **Identity disclosure.** An account holder's legal name, birth year,
   gender, marital status, place of civil registration or place of residence
   reaching a public schema, an unauthenticated response, an error report, or
   an agent-facing tool. Guards: `backend/tests/test_identity.py`,
   `backend/tests/test_observability.py`,
   `mcp-server/tests/test_redaction.py`.
3. **Moderation bypass.** A pending, rejected or suspended listing visible to
   an unauthenticated request — through search or through its direct
   `/business/{slug}` URL.
4. **Ownership scoping.** An owner-facing endpoint (`/api/my/*`) that trusts a
   business id from the request without filtering by the authenticated user's
   id.
5. **Data loss.** Anything that redeploys the `postgres` service, which has no
   persistent volume.
6. **Production safety weakened.** Loosening `Settings.enforce_production_safety()`
   so a deploy succeeds.

## Important — fix before merge unless the author says otherwise

- A user-facing string as a literal instead of a catalog key, or Arabic text
  in source (`backend/tests/test_i18n.py` is the guard, and it reads comments).
- A `VITE_` variable added to the Railway dashboard but not as an `ARG`+`ENV`
  pair in **both** Dockerfiles — the feature will look simply "not
  configured", with nothing in the logs to say why.
- A new owner-facing or public endpoint without a test asserting what it must
  *not* return.
- A repository method that makes an authorization decision. Repositories are
  the ORM layer; authorization belongs to services and API dependencies.
- Raw SQL where a repository method belongs.
- A claim in a PR description that was not actually verified.

## Worth raising — the author decides

- Naming, structure and duplication.
- A comment that explains *what* the code does rather than *why* it is that
  way.
- Missing test coverage for a branch that is cheap to cover.
- Accessibility on a new interactive element: focus visibility, an accessible
  name, and correct behaviour in both reading directions.

## Out of scope

- `frontend/package-lock.json` and other generated files.
- `backend/alembic/versions/*` beyond checking that a migration exists, is
  reversible, and that its presence was called out in the description.
- Locale catalogs, except that both `ar.json` and `en.json` carry the same
  keys.
- Formatting that `ruff` and `tsc` already decide.

## How to report

Most severe first. For each finding: the file and line, one sentence on the
defect, and a concrete failing scenario — inputs or state, and the wrong
result. A finding without a scenario is an impression, and impressions belong
in the last tier or nowhere.
