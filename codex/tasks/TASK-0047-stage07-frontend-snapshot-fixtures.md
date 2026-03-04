---
id: TASK-0047
epic: EPIC-090
title: "Export backend-owned frontend snapshot fixtures from real Stage06/Stage07 scenario states"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0045"]
risk: medium
context_packs: ["codex/context/EPIC-090.md", "codex/context/EPIC-040.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
TASK-0045 completed the Stage07 issue-scoped replan runtime slice (flags, activation, spawning, approval gating, delta promotion, lease recovery, reconcile).

What remained was a stable backend-owned snapshot fixture set for frontend parallel work:
- derived from real runtime scenario states,
- refreshable through a deterministic backend workflow,
- contract-tested so frontend branches can consume snapshots safely.

## Objective
Add backend-owned frontend snapshot fixtures generated from real scenario-backed runtime states and keep planning/task memory aligned.

Deliverables:
- deterministic snapshot export helper + script,
- committed JSON fixtures under `fixtures/frontend_contracts/`,
- contract test that regenerates snapshots and asserts committed fixtures match,
- docs/readme updates describing refresh workflow and scope.

This finalizes the backend side of the first Schedule Planning business wedge for parallel frontend/Kanban development.

## Non-goals
- Do not build frontend UI.
- Do not introduce board-local workflow semantics.
- Do not fork runtime business logic into snapshot generation.
- Do not create a second source of truth.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TEST_MATRIX.md`
- `codex/tasks/TASK-0045-stage07-issue-scoped-replan-loop.md`
- `tests/runtime/helpers/scenario_harness.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage07.py`

## Source files to change
- `tests/runtime/helpers/frontend_snapshots.py` (new)
- `scripts/export_frontend_snapshots.py` (new)
- `fixtures/frontend_contracts/` (new generated snapshot fixtures + README)
- `tests/runtime/contracts/test_frontend_snapshot_fixtures.py` (new)
- `tests/runtime/helpers/scenario_harness.py`
- `Makefile`
- `README.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/STAGE07_RUNTIME_MODEL.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=src pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_schedule_stage07_drift_detected.py`
- `pytest -q`

## Acceptance criteria
- backend-owned snapshot fixtures exist under `fixtures/frontend_contracts/`.
- snapshot fixtures are generated from real Stage06/Stage07 runtime scenario states (not hand-authored).
- snapshot export workflow is deterministic and documented.
- committed snapshots are protected by contract test coverage.
- Stage06 base schedule remains immutable; Stage07 snapshots reflect delta + audited pointer updates.
- planning/status/task memory is updated and non-stale.
- full repo verification loop passes.

## Notes
- `TASK-0044` already exists (HITL HTTP adapter), `TASK-0045` already exists (Stage07 runtime slice), and `TASK-0046` is in-progress frontend-shell work; this task therefore uses the next free ID (`TASK-0047`).
