---
id: TASK-0067
epic: EPIC-025
title: "Authored schedule-control semantics and canonical bridge artifacts for weekly/live logistics"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa"]
depends_on: ["TASK-0065", "TASK-0066"]
risk: high
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Land the authored semantics for schedule-control as the first serious agentic logistics slice, including:
- canonical route-slot requirements and driver-capability bridge artifacts,
- explicit Stage04/Stage02 bundle + candidate + validation outputs,
- explicit authority boundaries for derived current schedule and open exceptions.

## Non-goals
- no runtime schedule solver implementation in this task,
- no weekly multi-step agent loop in this task,
- no second truth path for current schedule or open exceptions,
- no new approval subsystem.

## Source Files Changed
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/weekly_schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/live_dispatch/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml`
- `schemas/artifacts/dataset_keys.yaml`
- `docs/workflows/weekly_schedule_planning/v1/examples/*`
- `docs/workflows/live_dispatch/v1/examples/*`
- `tests/contract/test_logistics_definition_contracts.py`
- `tests/unit/test_logistics_definition_compiler.py`
- `tests/unit/test_logistics_control_layer.py`
- `docs/examples/logistics_definitions/ACTIVATION_REQUEST.example.yaml`
- `docs/domains/logistics/current-state/CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0067-schedule-control-authored-semantics.md`

## Verification Run
- `make schema-validate`
- `pytest -q tests/contract/test_logistics_definition_contracts.py`
- `pytest -q tests/unit/test_logistics_definition_compiler.py tests/unit/test_logistics_control_layer.py`

All commands passed on 2026-03-12.

## Acceptance Criteria Coverage
- Weekly Stage04 and live Stage01/Stage02 authored surfaces now include explicit schedule-control bridge artifacts (`route_slot_requirements`, `driver_capabilities`, canonical input bundle, candidate delta, validation summary).
- Method package authored refs now identify shared schedule-control weekly/live mode surfaces for Stage04/Stage02.
- Contract and compiler tests assert new bridge semantics and guard against prohibited `current_schedule_plan`/`open_exceptions` peer truth keys.
- Current schedule authority remains derived and open exceptions remain sourced from canonical flags.

## Completion Notes (2026-03-12)
- Added canonical bridge artifacts and Stage04/Stage02 schedule-control semantics to weekly/live contracts, artifact maps, execution profiles, dataset registry, and examples.
- Added an explicit planning artifact-classification note (`docs/domains/logistics/current-state/CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md`) to lock canonical vs derived vs evidence vs prohibited surfaces.
- Updated contract/compiler/control-layer tests and activation request example to reflect expanded canonical bridge inputs while preserving one truth system invariants.
