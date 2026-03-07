---
id: TASK-0062
epic: EPIC-025
title: "Weekly to live handoff runtime and first logistics golden slice"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0061"]
risk: high
context_packs: ["codex/context/EPIC-025.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Land the first logistics composition/handoff runtime (`H`) over the fixed Strategy A substrate and the landed logistics definitions/control layers:
- add explicit handoff execution runtime state for `weekly_schedule_planning.Stage07 -> live_dispatch.Stage01`,
- materialize one logical daily seed per `ServiceDateID` from weekly Stage07 output,
- lazily activate live dispatch on first qualifying day-of event,
- preserve exact lineage/input bindings from weekly publish to daily seed to live activation to promoted live delta,
- prove behavior with a deterministic first end-to-end logistics golden scenario.

## Non-goals
- no availability-request downstream automation in this task,
- no reporting->planning or reporting->dispatch handoff runtime in this task,
- no timecard-audit runtime in this task,
- no live external connectors (fixture-only ingress remains required),
- no second officialness/runtime truth system.

## Test-First Plan
1. Add failing unit/runtime tests for typed week->day partition transform usage and explicit handoff execution record semantics.
2. Add failing tests for idempotent replay/recovery of handoff attempts and lazy live activation behavior.
3. Add failing tests for deterministic Stage07 daily seed materialization and same-scope lineage/input binding capture.
4. Add failing tests for ordered live delta promotion semantics and threshold-gated approval escalation.
5. Add failing golden scenario test for the first weekly->live deterministic acceptance slice.

## Oracle
Success is demonstrated by:
- explicit `edge_executions` runtime state exists and is idempotent/replay-safe,
- Stage07 seed materialization emits one logical seed per `ServiceDateID`,
- first day-of event lazily creates/resumes live dispatch activation using handoff state,
- lineage and exact input bindings are preserved across weekly publish -> seed -> live activation -> official delta,
- major-replan approval escalation occurs only when policy thresholds are crossed,
- first weekly->live golden scenario passes end-to-end.

## Source Files Planned
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/logistics_handoff_runtime.py`
- `src/onetruth/infrastructure/repositories/edge_executions.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/cli/__main__.py`
- `alembic/versions/*handoff*.py`
- `tests/unit/test_logistics_handoff_runtime.py`
- `tests/runtime/test_logistics_handoff_runtime.py`
- `tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `fixtures/scenarios/logistics/weekly_to_live_golden_slice.yaml`
- `docs/planning/LOGISTICS_WEEKLY_TO_LIVE_HANDOFF_RUNTIME.md`
- `docs/examples/logistics_definitions/*`
- status/task index docs

## Verification Run
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/contract`
- `pytest -q tests/unit/test_logistics_definition_compiler.py tests/contract/test_logistics_definition_contracts.py tests/unit/test_logistics_control_layer.py tests/contract/test_logistics_control_layer_contracts.py tests/runtime/test_logistics_control_layer_runtime_bridge.py`
- `pytest -q tests/unit/test_logistics_handoff_runtime.py tests/runtime/test_logistics_handoff_runtime.py tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py tests/runtime/scenarios/test_workspace_graph_projection.py tests/runtime/api/test_workflow_run_workspace_endpoint.py`
