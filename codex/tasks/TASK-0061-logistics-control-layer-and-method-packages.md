---
id: TASK-0061
epic: EPIC-025
title: "Logistics control layer and pinned method packages over canonical runtime activations"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0060"]
risk: high
context_packs: ["codex/context/EPIC-025.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Land the first logistics control (`C`) slice as compiled deterministic metadata over existing runtime objects:
- compile stage-level execution control specs from family definitions + execution profiles + authored method packages,
- pin method packages with stable digests and execution-spec identities,
- validate logistics activation requests against compiled definitions,
- derive execution-session payload metadata from compiled control specs without introducing a second activation ontology.

## Non-goals
- no handoff execution runtime/state machine,
- no new canonical activation tables,
- no live connector execution,
- no LLM-driven ranking authority (LLM rationale remains optional and bounded only).

## Test-First Plan
1. Add unit tests for deterministic control compilation, method-package identity pinning, activation validation, fail-closed missing metadata, and no-second-activation guarantees.
2. Add contract tests for new schemas and logistics control-layer authored/examples surfaces.
3. Add a runtime bridge test proving compiled control metadata drives existing `execution_sessions` via current CLI/runtime semantics.

## Oracle
Success is demonstrated by:
- deterministic compiled stage execution specs for first-slice logistics stages,
- method-package pins that change when behavior package content changes,
- activation request validation driven only by compiled definitions and canonical pointer-address inputs,
- execution-session payload derivation that maps into existing runtime objects,
- explicit fail-closed behavior when required control metadata is missing.

## Source Files Changed
- `docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml`
- `schemas/workflows/method_package.schema.json`
- `schemas/workflows/compiled_stage_execution_spec.schema.json`
- `schemas/workflows/activation_request.schema.json`
- `src/onetruth/infrastructure/definitions/control_layer.py`
- `src/onetruth/infrastructure/definitions/__init__.py`
- `scripts/validate_repo.py`
- `tests/unit/test_logistics_control_layer.py`
- `tests/contract/test_logistics_control_layer_contracts.py`
- `tests/runtime/test_logistics_control_layer_runtime_bridge.py`
- `docs/examples/logistics_definitions/ACTIVATION_REQUEST.example.yaml`
- `docs/examples/logistics_definitions/COMPILED_STAGE_EXECUTION_SPEC.example.yaml`
- `docs/examples/logistics_definitions/README.md`
- `docs/workflows/logistics_ops_family/v1/README.md`
- `docs/workflows/README.md`
- `docs/planning/LOGISTICS_CONTROL_LAYER_AND_METHOD_PACKAGES.md`
- `codex/tasks/TASK-0061-logistics-control-layer-and-method-packages.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Verification Commands
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/contract`
- `pytest -q tests/unit/test_logistics_definition_compiler.py tests/contract/test_logistics_definition_contracts.py`
- `pytest -q tests/unit/test_logistics_control_layer.py tests/contract/test_logistics_control_layer_contracts.py tests/runtime/test_logistics_control_layer_runtime_bridge.py`

## Acceptance Criteria
- Compiled stage control metadata exists, is deterministic, and maps only to canonical runtime objects.
- Method-package pinning is explicit and replay/review-safe.
- Activation requests are validated from compiled definitions and canonical pointer references.
- Missing required control metadata fails closed.
- Slice is ready for explicit handoff runtime work (Agent 03 scope).

## Completion Notes (2026-03-07)
- Added authored logistics method-package registry and control-layer schemas.
- Added deterministic control compiler/service with stage execution specs, method-package pinning, activation validation, and execution-session payload derivation.
- Proved runtime bridging through existing `workflow_runs` / `task_runs` / `human_tasks` / `execution_sessions` / `tool_executions` semantics.
- Preserved one activation ontology; no new activation runtime table/model was introduced.
