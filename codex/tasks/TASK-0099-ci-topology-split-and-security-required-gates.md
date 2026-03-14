---
id: TASK-0099
epic: EPIC-080
title: "Split CI into fast required checks and runtime required checks, and add security gates"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0090", "TASK-0091"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: []
---

## Context
The repo's CI posture was still asymmetrical: the main PR workflow used one monolithic backend lane, `ci-backend` did not include `unit` or `security`, and the dedicated `secret_hygiene` workflow was present but not clearly reflected in the required-lane story.

This task makes the CI topology truthful and easier to reason about without broadening into hosted branch-protection enforcement or real-network gate changes.

## Objective
Split CI into parallel fast required backend lanes plus one explicit runtime-required lane, keep frontend separate, and make security guardrails first-class in the documented PR posture.

## Non-goals
- No hosted GitHub branch-protection changes from repo code.
- No change to OpenAI integration gating semantics.
- No broad test-suite refactor beyond naming and slicing existing CI truth.

## Source Files Changed
- `.github/workflows/main.yml`
- `.github/workflows/agent_api.yml`
- `Makefile`
- `tests/contract/test_repo_automation_truth.py`
- `README.md`
- `codex/tasks/TASK-0099-ci-topology-split-and-security-required-gates.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- CI topology and repo-automation documentation only.

## Plan
1. Freeze the workflow shape in contract tests before changing YAML.
2. Split local Make targets into fast-backend and runtime-required slices so CI and local truth match.
3. Recompose the main workflow into parallel fast required lanes, one runtime-required lane, and post-merge/manual release-confidence slices.
4. Retarget `agent_api` to the fast backend aggregate and update repo memory/docs to match.

## Verification Run
- `python3 scripts/validate_repo.py --schemas-only`
- `pytest -q tests/contract/test_repo_automation_truth.py`
- `make unit`
- `make security`
- `make lint`
- `make ci-backend`
- `python3 - <<'PY'` YAML inspection of `main.yml` job graph and triggers

## Acceptance Criteria Coverage
- Required PR checks now explicitly include lint, contract, unit, and security as separate fast lanes.
- Heavier replay/acceptance/runtime coverage remains required but isolated to one `runtime-required` lane.
- `release-confidence` no longer adds pull-request lane count and instead runs on `push` to `main` plus `workflow_dispatch`.
- `secret_hygiene` remains a distinct PR-capable workflow, and `agent_api` now reuses the fast backend aggregate instead of the heavy backend aggregate.

## Completion Notes (2026-03-14)
- Replaced the single `backend` PR job in `.github/workflows/main.yml` with a `required-fast` matrix over `lint`, `contract`, `unit`, and `security`, plus a separate `runtime-required` job and unchanged standalone `frontend` lane.
- Moved `release-confidence` off pull requests by gating it to `push` and `workflow_dispatch`, while keeping its existing matrix slices intact.
- Added `ci-fast-backend` and `ci-runtime-required` as truthful local/CI Make targets and kept `ci-backend` as the aggregate alias over both.
- Retargeted `.github/workflows/agent_api.yml` so the non-network baseline runs `ci-fast-backend` before the existing gated OpenAI integration tests.
- Documented that stable workflow/job names can be made required in hosted branch protection, but that enforcement remains an operator-side GitHub setting rather than repo-enforceable code.
