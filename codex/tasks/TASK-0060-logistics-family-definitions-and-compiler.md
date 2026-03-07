---
id: TASK-0060
epic: EPIC-025
title: "Logistics family definitions and deterministic fail-closed compiler"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0059"]
risk: high
context_packs: ["codex/context/EPIC-025.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Land the first logistics definitions slice as a monotone extension over the fixed Strategy A substrate seam:
- import canonical logistics workflow packs,
- add authored workflow-family and typed partition-transform surfaces,
- add deterministic fail-closed family compilation for `weekly_schedule_planning.v1 -> live_dispatch.v1`,
- keep the rest of the logistics family visible as staged extension/deferred modules.

## Non-goals
- no runtime composition execution surface,
- no new activation model,
- no live external connector wiring,
- no availability/reporting/timecard runtime handoff execution in this task,
- no reopening of state-plane migration or pointer identity semantics.

## Test-First Plan
1. Add contract tests for imported logistics workflow packs and family/transform schema surfaces.
2. Add unit tests for deterministic compiled module and edge descriptors.
3. Add fail-closed negative tests for missing first-slice handoff semantics.
4. Add typed partition-transform mismatch tests to prevent stringly-typed transform drift.

## Oracle
Success is demonstrated by:
- logistics authored packs validating under repo contract rules,
- workflow-family and partition-transform authored surfaces validating,
- deterministic compilation producing stable module/edge descriptors,
- compile-time rejection of underspecified/ambiguous semantics,
- typed partition transform checks enforced through compiled edge validation.

## Source Files Changed
- `docs/workflows/weekly_schedule_planning/v1/*`
- `docs/workflows/live_dispatch/v1/*`
- `docs/workflows/availability_request/v1/*`
- `docs/workflows/dispatch_reporting/v1/*`
- `docs/workflows/timecard_audit/v1/*`
- `docs/workflows/TARGET_DOMAIN_PACKS_OVERVIEW.md`
- `docs/workflows/logistics_ops_family/v1/*`
- `docs/examples/logistics_definitions/*`
- `schemas/artifacts/dataset_keys.yaml`
- `schemas/workflows/workflow_family.schema.json`
- `schemas/workflows/partition_transform_registry.schema.json`
- `schemas/workflows/compiled_module_definition.schema.json`
- `schemas/workflows/compiled_family_edge.schema.json`
- `schemas/workflows/state_ref.schema.json`
- `src/onetruth/domain/partition_codec.py`
- `src/onetruth/infrastructure/definitions/family_compiler.py`
- `src/onetruth/infrastructure/definitions/__init__.py`
- `scripts/validate_repo.py`
- `tests/contract/test_logistics_definition_contracts.py`
- `tests/unit/test_logistics_definition_compiler.py`
- `docs/planning/LOGISTICS_FAMILY_DEFINITIONS_AND_COMPILATION.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `codex/tasks/TASK-0060-logistics-family-definitions-and-compiler.md`

## Verification Commands
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/contract`
- `pytest -q tests/unit/test_logistics_definition_compiler.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`

## Acceptance Criteria
- Logistics workflow packs are imported as canonical authored assets.
- Family/module/edge/partition definition surfaces exist and validate.
- Deterministic fail-closed definition compilation is implemented and test-pinned.
- Example/template artifacts for family/module/method/handoff/partition/scenario are present in-repo.
- No runtime composition logic is introduced in this slice.

## Completion Notes (2026-03-07)
- Landed the logistics workflow authored packs and target-domain overview as repo-native source.
- Added typed family/transform schema surfaces and deterministic compile-time descriptor generation.
- Pinned fail-closed behavior for missing first-slice semantics and partition-transform kind mismatches.
- Kept composition execution state/runtime handoff behavior explicitly out of scope.
