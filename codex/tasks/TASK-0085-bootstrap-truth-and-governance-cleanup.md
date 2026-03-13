---
id: TASK-0085
epic: EPIC-080
title: "Bootstrap truth, CI honesty, and governance cleanup"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0075"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-009"]
---

## Context
Several day-to-day repo claims are softer than they sound. The tranche needs one honest bootstrap/doctor posture, truthful lint/CI targets, explicit runtime versions, and basic governance hygiene before deeper hardening work continues.

## Objective
Make the repo’s day-to-day developer posture truthful: real lint, one obvious bootstrap/doctor path, explicit runtime version expectations, CODEOWNERS validation, and a license.

## Non-goals
- No heavyweight internal developer platform.
- No target renames without making behavior clearer.
- No slow or nondeterministic bootstrap checks.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- `Makefile`
- `.github/workflows/main.yml`
- `.github/CODEOWNERS`
- `frontend/package.json`
- `README.md`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `Makefile`
- `.github/workflows/main.yml`
- `.github/CODEOWNERS`
- `frontend/package.json`
- `.nvmrc`
- `scripts/bootstrap_dev.sh` or `scripts/doctor.py`
- `LICENSE`
- `tests/contract/test_codeowners_paths.py`
- `README.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0085-bootstrap-truth-and-governance-cleanup.md`

## Generated / downstream artifacts impacted
- CI/bootstrap contract coverage only.

## Plan
1. Audit current repo claims that need to become executable checks.
2. Add one lightweight bootstrap or doctor path.
3. Make CODEOWNERS paths, versions, and governance basics explicit and testable.
4. Keep the resulting checks cheap enough for fresh Codex sessions.

## Verification
- `make lint`
- `make ci`
- `pytest tests/contract/test_codeowners_paths.py -q`
- `./scripts/bootstrap_dev.sh --check` or equivalent

## Acceptance criteria
- `make lint` reflects real lint/validation behavior.
- There is one obvious bootstrap/doctor path for humans and Codex.
- Runtime version expectations, CODEOWNERS validity, and license presence are explicit and testable.
- The task remains lightweight and deterministic.

## Notes / decisions
- Repo claims should map to executable checks after this task.
