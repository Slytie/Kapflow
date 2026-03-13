---
id: TASK-0086
epic: EPIC-040
title: "First controlled hotspot extraction after invariants are stable"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0080", "TASK-0081", "TASK-0082", "TASK-0083"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-060.md", "codex/context/EPIC-030.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-003"]
---

## Context
`workflow_task_lifecycle.py` has grown into a real hotspot. The tranche defers extraction until the surrounding invariants are frozen so the first move can be small, characterized, and compatible.

## Objective
Perform the first controlled extraction from `workflow_task_lifecycle.py` only after the invariant tasks are complete and green, choosing one bounded flow family with compatibility seams and characterization tests.

## Non-goals
- No extraction before `TASK-0080` through `TASK-0083` are complete.
- No flag-day import churn.
- No decomposition of unresolved semantics.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-030.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `tests/runtime/api/*`
- `tests/security/*`
- `tests/unit/*`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-030.md`
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- new handler modules under `src/onetruth/application/handlers/`
- relevant characterization tests
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/tasks/TASK-0086-first-controlled-hotspot-extraction.md`

## Generated / downstream artifacts impacted
- None expected beyond task-memory and characterization coverage.

## Plan
1. Choose the first extraction target by cohesion and risk, not raw file size.
2. Add any missing characterization tests before moving logic.
3. Extract one bounded flow family behind compatibility re-exports.
4. Keep callers stable while the new seam proves itself.

## Verification
- Targeted pytest slices for the extracted command family
- `python3 scripts/validate_repo.py --schemas-only`
- import-cycle check if a repo-native rule exists by then

## Acceptance criteria
- One bounded flow family is extracted behind compatibility seams.
- Characterization tests freeze behavior before and after the move.
- No new import cycles or broad churn are introduced.
- The task starts only after the earlier invariant tasks are complete and green.

## Notes / decisions
- The first extraction should optimize for risk reduction, not for LOC moved.
- Completed 2026-03-13 with an approvals-first seam:
  - added `src/onetruth/application/handlers/approvals.py` for `request/respond/show/list`
  - kept `workflow_task_lifecycle.py` import-compatible through thin lazy wrappers
  - added `tests/unit/test_approval_handler_compatibility.py` to freeze legacy-vs-new handler behavior
