---
id: TASK-0045
epic: EPIC-040
title: "Implement first Stage07 issue-scoped replan loop over canonical runtime"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0044"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-090.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-008"]
---

## Context
TASK-0040 .. TASK-0044 implemented the canonical substrate, Stage06 publish slice, scenario harness, and thin board/query HTTP adapter.

Stage07 issue-loop semantics were still missing:
- no canonical flag current-state table wired into runtime commands,
- no issue-scoped activation key dedupe path,
- no Stage07 completion outcome -> child spawn mapping in the transactional completion path,
- no major-replan approval gate at promotion time,
- no lease-expiry reopen/reconcile implementation-backed tests for Stage07 issue work.

## Objective
Implement the first Stage07 issue-scoped replan runtime slice using canonical substrate semantics:
- canonical `flags` persistence + lifecycle commands,
- issue activation inside the same workflow run with activation-key+generation dedupe,
- Stage07 completion-driven child spawning with lineage fields,
- major-replan approval gating via canonical approvals,
- Stage07 delta/pointer drift evidence (`artifact.pointer.drift_detected`) without mutating Stage06 base schedule,
- lease-expiry reopen + Stage07 reconcile recovery commands,
- scenario-backed runtime + query-contract tests.

This is the backend completion of the first Schedule Planning business wedge.

## Non-goals
- Do not build frontend UI.
- Do not introduce a second source of truth.
- Do not generalize into a broad workflow engine abstraction.
- Do not implement execution-session/tool policy gate runtime yet.
- Do not mutate Stage06 base schedule artifact versions in place.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`

## Source files changed
- `src/onetruth/infrastructure/db/models.py`
- `alembic/versions/20260303_0004_stage07_flags_and_lineage.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/flags.py` (new)
- `src/onetruth/infrastructure/repositories/task_runs.py`
- `src/onetruth/infrastructure/repositories/human_tasks.py`
- `src/onetruth/infrastructure/repositories/workflow_runs.py`
- `src/onetruth/application/services/schedule_planning_stage07.py` (new)
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/cli/__main__.py`
- `tests/runtime/helpers/scenario_harness.py`
- `fixtures/scenarios/schedule_planning/stage07_*.yaml` (new)
- `tests/runtime/scenarios/test_schedule_stage07_*.py` (new)
- `tests/runtime/contracts/test_hitl_query_contracts_stage07.py` (new)
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`
- `tests/runtime/api/test_human_task_list_contract.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `tests/runtime/api/test_workflow_run_detail_contract.py`
- docs/README/task/status/planning files listed below

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_missing_information_branch.py`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_child_issue_branch.py`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_duplicate_flag_retry.py`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_lease_expiry_recovery.py`
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_drift_detected.py`
- `pytest -q tests/runtime/contracts/test_hitl_query_contracts_stage07.py`
- `pytest -q`

## Acceptance criteria
- canonical `flags` support exists with migrations.
- Stage07 issue activation exists and dedupes by activation key + generation.
- Stage07 completion supports explicit bounded child spawning with lineage fields.
- major-replan approval gating is enforced through canonical approval model.
- Stage07 delta artifact semantics are implemented without base-schedule mutation.
- lease-expiry recovery + reconcile exist with authoritative event evidence.
- Stage07 scenario fixtures/tests exist and run through CLI command boundary.
- Stage07 query-contract tests exist for flags/task/approval/pointer/workflow/board read surfaces.
- `docs/planning/STAGE07_RUNTIME_MODEL.md` exists and matches implementation.
- README/planning/status/task memory is updated and non-stale.
- full repo verification passes.

## Implementation notes
- Flag states in this slice: `open`, `triage`, `blocked`, `resolved`, `closed`, `waived`.
- Lease expiry policy in this slice: reopen the same human-task row; no escalation task creation.
- Major-replan marker: `promotion_reason=official_major_replan`.
- Drift policy: emit `artifact.pointer.drift_detected` when reviewed base is stale and keep promotion allowed.
- Stage07 activation/reconcile and child spawn behavior are lineage-ready for future deeper business rules without introducing a second truth path.
