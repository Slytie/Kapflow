---
id: TASK-0063
epic: EPIC-025
title: "Generic notify_only handoff runtime and reporting-to-planning slice"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0062"]
risk: high
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Generalize logistics handoff runtime behavior with an explicit first-class `notify_only` mode over the existing compiled-family + `edge_executions` substrate, and land the first reporting->planning feedback slice:
- `dispatch_reporting.Stage05 -> weekly_schedule_planning.Stage03`
- deterministic typed `ServiceDateID -> PlanningWeekID` transform
- idempotent target run resolve/create
- canonical target input materialization + exact input binding capture
- `writer_mode: source_only` preserved (no target official-output promotion in notification path)

## Non-goals
- no availability-request runtime in this task
- no timecard-audit runtime in this task
- no content-derived transform semantics
- no live connector integrations
- no second composition model or second activation ontology

## Test-First Plan
1. Add failing tests for generic `notify_only` dispatch over compiled family edges.
2. Add failing tests for idempotent target run resolution/creation and edge reuse on duplicate notifications.
3. Add failing tests for canonical target input artifact materialization + exact binding capture without target official-output mutation.
4. Add failing deterministic scenario coverage for reporting->planning notify-only feedback.

## Oracle
Success is demonstrated by:
- `notify_only` runtime behavior is explicit and routed through compiled family edge descriptors + typed transform registry,
- `reporting_actuals_to_future_planning` resolves `ServiceDateID -> PlanningWeekID` deterministically and reuses the same logical `edge_execution` on retries,
- target weekly planning run is resolved/created idempotently and receives canonical `planning.actual_hours_snapshot.workbook` input materialization + `stage03.actual_hours_snapshot` binding,
- target official-output pointers/artifacts are not mutated by notification,
- reporting->planning scenario slice passes deterministically end-to-end.

## Source Files Changed
- `src/onetruth/application/services/logistics_handoff_runtime.py`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `src/onetruth/cli/__main__.py`
- `tests/unit/test_logistics_handoff_runtime.py`
- `tests/runtime/test_logistics_handoff_runtime.py`
- `tests/runtime/helpers/scenario_harness.py`
- `fixtures/scenarios/logistics/reporting_to_planning_notify_only_golden_slice.yaml`
- `tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py`
- status/task-index/docs updates

## Verification Run
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/unit/test_logistics_handoff_runtime.py`
- `pytest -q tests/runtime/test_logistics_handoff_runtime.py`
- `pytest -q tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py`

## Completion Notes (2026-03-08)
- Added `handoffs notify-only` CLI/runtime behavior that resolves handoff semantics from compiled logistics family edges.
- Landed reporting->planning notify-only feedback with deterministic transform, target run idempotency, canonical target input materialization, and exact input bindings.
- Added deterministic runtime/scenario coverage and preserved one-truth substrate constraints (`edge_executions`, canonical artifacts/bindings, no second activation model).
