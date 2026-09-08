#!/usr/bin/env bash
#
# Run pytest and publish what happened as step outputs, so the pull request
# comment can show test counts rather than only a green tick.
#
# A wrapper rather than inline YAML because the same logic is needed by two
# jobs, and because `set -o pipefail` plus a heredoc-delimited multi-line
# output is exactly the kind of shell that goes wrong unnoticed when it is
# duplicated and edited in one place only.
#
# Usage: run-pytest.sh <pytest-command> [args...]

set -uo pipefail

log="$(mktemp)"

# Not `set -e`: the exit code has to survive so the summary can be published
# for a failing run too. A comment that only appears when tests pass is a
# comment that never tells you anything you did not already know.
"$@" -q --color=no 2>&1 | tee "$log"
status="${PIPESTATUS[0]}"

# pytest's own last line: "204 passed in 205.33s (0:03:25)", or on failure
# "3 failed, 201 passed in 198.11s". Strip the ANSI-free separators pytest
# pads it with.
summary="$(grep -E '[0-9]+ (passed|failed|error)' "$log" | tail -1 | tr -d '=' | xargs || true)"
if [ -z "$summary" ]; then
  # Died before any test ran -- a collection error, a missing dependency, an
  # unrecognised flag. Say that, rather than reporting an empty result as if
  # the suite had passed silently.
  summary="no test summary produced (exit ${status})"
fi

{
  echo "summary=${summary}"
  echo 'failures<<PYTEST_FAILURES'
  # Node ids only: a full traceback belongs in the run log, but the names
  # are what tell a reviewer whether a failure is theirs.
  grep -E '^(FAILED|ERROR) ' "$log" | head -25 || true
  echo 'PYTEST_FAILURES'
} >> "${GITHUB_OUTPUT:-/dev/null}"

# Also on the run's own summary page, where someone who clicked through
# expects to find it.
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  echo "### ${summary}" >> "$GITHUB_STEP_SUMMARY"
  grep -E '^(FAILED|ERROR) ' "$log" | head -25 >> "$GITHUB_STEP_SUMMARY" || true
fi

exit "$status"
