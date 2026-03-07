---
id: TASK-0059
epic: EPIC-030
title: "Strategy A strong closure for canonical pointer identity"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0030", "TASK-0042", "TASK-0057"]
risk: high
context_packs: ["codex/context/EPIC-030.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Objective
Finish Strategy A strong closure so canonical pointer identity is authoritative end-to-end for:
- authoritative pointer promotion writes,
- pointer promotion/drift event payload semantics,
- public pointer query surfaces,
- workspace/demo/export official-output projections.

This task closes the remaining compatibility debt seam without introducing a second officialness model.

## Non-goals
- no logistics tranche behavior,
- no new workflow-family handoff runtime logic,
- no second truth system for officialness,
- no authorization/scope relaxations,
- no broad physical schema rewrite beyond what canonical closure strictly needs.

## Test-First Plan
1. Add regressions that prove `artifact.pointer.promoted` and `artifact.pointer.drift_detected` emit canonical pointer identity semantics.
2. Add regressions for canonical pointer read queries (`pointer_id` and canonical address filters) on `/api/v1/pointers`.
3. Add regressions that keep workspace/export official-output behavior correct under canonical pointer identity.
4. Add fail-closed regression for promotions when canonical pointer identity cannot be safely resolved.
5. Add/adjust property coverage so canonical event payload fields remain aligned with canonical pointer address semantics.

## Oracle
Closure is proven by:
- pointer events carrying canonical `pointer_id` and canonical `dataset_key` semantics,
- canonical pointer query filters working without run-local identity assumptions,
- unchanged demo/export official-output correctness under same-scope cross-run pointer targets,
- fail-closed denial on unresolved canonical pointer identity,
- green baseline contract/security/unit/property/runtime suites.

## Source Files Changed
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `tests/property/test_pointer_dual_write_consistency.py`
- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `tests/runtime/api/test_pointer_list_endpoint.py`
- `tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `docs/planning/STRATEGY_A_STRONG_CLOSURE.md`
- `docs/planning/STRATEGY_A_STRONG_CLOSURE_REPORT.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `codex/tasks/TASK-0059-strategy-a-strong-closure.md`

## Verification Commands
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/contract`
- `pytest -q tests/security`
- `pytest -q tests/unit/test_pointer_address_resolution.py tests/unit/test_artifact_provenance_dag.py tests/unit/test_workflow_run_input_bindings.py`
- `pytest -q tests/property/test_pointer_dual_write_consistency.py tests/property/test_provenance_projection_compatibility.py`
- `pytest -q tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`
- `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --db-url sqlite:///.tmp/strategy_a_strong_closure.db --scenario stage06_publish_ready --pilot-key strategy-a-strong-closure --output-root .tmp/strategy_a_strong_closure_artifacts --output-json .tmp/strategy_a_strong_closure_output.json`
- `PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py --db-url sqlite:///.tmp/strategy_a_strong_closure.db --workflow-run-id <run_id> --output .tmp/strategy_a_strong_closure_bundle.zip`

## Acceptance Criteria
- Canonical pointer identity is authoritative in writes/events/public reads/demo official-output projections.
- Legacy `(workflow_run_id, pointer_key)` remains compatibility-only, not semantic owner.
- Docs/schemas/runtime behavior describe one pointer identity truth.
- Baseline closure suites and demo/export commands pass from clean setup.
- Next tranche can be monotone over this substrate without reopening pointer identity migration.

## Completion Notes (2026-03-07)
- Closed a residual seam where pointer event payload `dataset_key` could mirror non-canonical legacy casing from `artifact_kind` instead of canonical pointer identity semantics.
- Added fail-closed runtime regression for unresolved canonical pointer identity.
- Extended API/runtime/demo/export regressions for canonical `pointer_id` query and official-output pointer identity assertions.
- Confirmed compatibility aliases remain intentionally supported while canonical identity is authoritative.
