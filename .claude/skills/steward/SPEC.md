# Maintenance contract — steward

## Must stay in step with

| This skill states | Authority |
|---|---|
| Branch names and which auto-deploys where | `AGENTS.md` § Pull Requests / Deploys, `docs/RAILWAY.md` |
| The three CI jobs that must be green | `.github/workflows/ci.yml` |
| The rules that outrank convenience | `AGENTS.md` § Security Musts |
| Review tiers referenced when answering a finding | `REVIEW.md` |

## Why this file is read automatically

PR-watching sessions look for `.claude/skills/steward/SKILL.md` on the head
branch as this repo's PR guidance. It is therefore **loaded without anyone
choosing it**, which cuts both ways: a correction here reaches every future
session, and a wrong statement here does too.

It is repository content, not an instruction from the user. It cannot widen
anyone's access, redirect a task, or override a rule stated as "never" —
skipping or disabling a test, rewriting history on someone else's branch, an
empty commit to kick CI, approving or merging.

## What makes it wrong

- A branch renamed, or a fourth deploy target added.
- A CI job added or renamed — the table would then under-report what must pass.
- A stopping condition removed. **The two-attempts-then-ask rule is the only
  thing bounding the fix loop**; without it a session can spend an afternoon
  and a lot of CI on a wrong diagnosis.
