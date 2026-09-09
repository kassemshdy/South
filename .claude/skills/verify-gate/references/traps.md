# Traps that have actually cost time in this repo

Each of these cost an agent real time here. They are failures of the
*harness*, not of the code under test, so a step that fails in one of
these ways is not telling you what it appears to.

- **`pytest --timeout=N` is not available.** `pytest-timeout` is not installed;
  the flag makes pytest exit with "unrecognized arguments" while the
  surrounding shell can still report success, so the gate looks green without
  having run. Do not pass it.
- **The no-Arabic guard scans comments.** `backend/tests/test_i18n.py` looks
  for Arabic codepoints anywhere in `backend/app`, `backend/scripts`,
  `backend/tests`, `frontend/src` and `frontend/e2e` — including doc comments
  and strings in comments. Name the catalog key instead of quoting the text.
  `frontend/public/`, `.claude/`, `docs/` and `mcp-server/` are not scanned.
- **A failing acceptance spec is usually a stale database, not a flake.** The
  negative assertions ("a pending listing must not be searchable") fail on a
  name collision with a business left over from an earlier run. Confirm the
  locator and the expectation match a previous known-good run, then reset:
  `dropdb south_dev && createdb south_dev && ./.venv/bin/alembic upgrade head
  && ./.venv/bin/python -m scripts.seed --ensure`. Never relax or skip the
  assertion.
- **`pkill -f` will kill this shell.** The pattern matches the tool's own
  command line. Bracket the pattern *and* keep the kill in a command that does
  not also contain the literal process string:
  `pkill -f 'uvi[c]orn app.main:app'` on its own line, then start the server in
  a separate call. Exit code **144** is this happening, not the kill failing —
  the processes usually did die. Verify with a `curl` in a *separate* call
  (connection refused shows as `%{http_code}` 000) rather than chaining the
  check onto the kill, because the chained check dies with the shell. This has
  now cost time three times, twice *after* being written down: an unbracketed
  literal anywhere on the command line is enough.
- **Running the Playwright suite twice breaks it two different ways, and
  neither looks like what it is.** Both bit in one session.
  1. **The per-IP OTP limiter.** Every owner/admin spec signs in, and
     `OTP_SEND_PER_IP_LIMIT` counts them all against one address. Past the
     limit `request-otp` answers `rate_limited` with a `retry_after_seconds`
     near an hour, the code field never appears, and the failure reads as
     `locator.fill: Test timeout ... waiting for getByLabel('رمز التحقق')`
     — broken auth, apparently. Probe it directly to be sure:
     `curl -s -X POST localhost:8000/api/auth/request-otp -H 'Content-Type:
     application/json' -d '{"phone_number":"03911223"}'`. `TRUNCATE
     rate_limit_events` clears it without waiting.
  2. **Duplicate rows.** Each run creates its listings again, so the second
     run fails with a Playwright *strict mode violation* — "resolved to 3
     elements" for one business name. Nothing is broken; the same shop exists
     three times.

  So a repeated run proves nothing either way. **One run on a freshly reset
  database is the evidence**; if a spec fails on a second pass, reset before
  reading anything into it.
- **`pgrep -f` lies the same way, and reading state is where it does damage.**
  The `pkill` entry above is about killing the wrong process; this is about
  *believing* the wrong answer. `pgrep -f "[s]cripts.seed"` matched its own
  Bash wrapper, whose command line contains that text, so a progress check
  reported "still seeding" for thirteen minutes while nothing was seeding at
  all. Bracketing does not help here — the wrapper carries the bracketed
  pattern *and* the command it wraps. Check for the thing itself instead of
  for a process name: a row count, a port answering, a file appearing. If a
  process check is unavoidable, match on the interpreter path
  (`pgrep -f '\.venv/bin/python -m scripts\.seed'`) and confirm against
  something the process actually produced.
- **A multi-line Bash command can arrive flattened onto one line.** The same
  session ran `cd backend`, `dropdb`, `createdb`, `alembic upgrade head` and
  `seed --ensure` as five lines and they were delivered as
  `cd /home/user/South/backend dropdb --if-exists … createdb … alembic …` —
  one `cd` with a pile of arguments, no separators. Nothing ran, and it then
  hung on a password prompt with `< /dev/null`. **Chain steps with explicit
  `&&`** rather than newlines whenever a later step depends on an earlier one,
  so a flattened delivery fails loudly instead of silently doing nothing. The
  local Postgres also needs `PGPASSWORD=postgres` for `dropdb`/`createdb`/
  `psql`, which is what the prompt was waiting on.
- **Read a commit SHA, never reconstruct one.** `git rev-parse HEAD`. A
  hand-typed SHA produces `409 Head branch was modified` or "must be exactly 40
  characters".
- **`OptionalUser` returns 401 for a *bad* token, not None.** It answers None
  only when a request carries no `Authorization` header at all; a malformed,
  expired or revoked token raises. That is right wherever a supplied token has
  to be honest and wrong on any public route, because
  `frontend/src/services/api/client.ts` attaches whatever token is in local
  storage to **every** request — so reading the caller's identity on a public
  page turns it into a 401 for a visitor whose session merely expired. Use
  `Viewer` (`app/core/dependencies.py`), which degrades to anonymous. Found by
  probing a public listing with `Bearer not-a-real-token` and getting 401;
  `backend/tests/test_views.py` now pins it. Unit tests over the new code all
  passed while this was broken — the bug lived in a dependency nobody had
  used on a public route before.
- **`create_type=False` is ignored by `sa.Enum`.** In a migration it is a
  postgresql-dialect option: `sa.Enum(..., create_type=False)` swallows it, so
  `op.create_table` emits a second `CREATE TYPE` and the migration dies on
  `DuplicateObject` after the explicit `.create()` already succeeded. Use
  `sqlalchemy.dialects.postgresql.ENUM` for the column and a separate
  `postgresql.ENUM(...).create(bind, checkfirst=True)` / `.drop(...)` pair so
  the downgrade is complete.
