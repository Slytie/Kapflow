# STRATEGY_A_STRONG_CLOSURE_REPORT.md

Date: 2026-03-07
Scope: Final Strategy A strong closure cleanup for canonical pointer identity semantics.

## 1) Remaining semantic drift before this pass
The remaining closure seam was not structural identity ownership; it was semantic leakage in authoritative pointer events:
- `artifact.pointer.promoted.payload.dataset_key` and `artifact.pointer.drift_detected.payload.dataset_key` could mirror caller-provided `artifact_kind` casing.
- This allowed non-canonical dataset-key representation in authoritative event payloads even when canonical pointer identity was already resolved.

Resulting risk:
- event consumers could observe canonical `pointer_id` but non-canonical dataset-key payload representation.

## 2) What changed
Runtime changes:
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
  - promotion handler now derives pointer-event `dataset_key` from canonical pointer identity semantics (`pointer` row / canonical identity), not raw caller `artifact_kind` input.
  - retained fail-closed guard when canonical pointer identity/dataset semantics cannot be resolved.

Test changes (test-first + regressions):
- `tests/property/test_pointer_dual_write_consistency.py`
  - added event payload canonicality assertions (`pointer_id` + canonical `dataset_key`) under mixed legacy-casing inputs.
- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
  - added canonical payload tests for `artifact.pointer.promoted` and `artifact.pointer.drift_detected`.
  - added fail-closed promotion test for unresolved canonical pointer identity.
- `tests/runtime/api/test_pointer_list_endpoint.py`
  - added canonical pointer-id query regression (`/api/v1/pointers?pointer_id=...`).
- `tests/runtime/api/test_workflow_run_workspace_endpoint.py`
  - added canonical pointer-id assertions in official-output workspace projection.
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
  - added canonical pointer-id assertions in export bundle official-output payload.

Docs/task/status alignment:
- created `codex/tasks/TASK-0059-strategy-a-strong-closure.md`
- created `docs/planning/STRATEGY_A_STRONG_CLOSURE.md`
- updated `docs/planning/EVENT_EMISSION_MATRIX.md`
- updated `docs/planning/TASK_INDEX.md`
- updated `docs/status/CURRENT_FOCUS.md`

## 3) Physical PK replacement status
No additional physical PK replacement was required in this pass.

Status:
- canonical pointer-PK migration already exists in `alembic/versions/20260307_0008_pointer_identity_strong_closure.py`.
- this pass intentionally preserved legacy compatibility carriers (`workflow_run_id`, `pointer_key`) as aliases only.

## 4) Verification commands and results
Baseline suite (rerun after changes):
- `make schema-validate` - passed
- `python3 scripts/validate_repo.py` - passed
- `pytest -q tests/contract` - passed
- `pytest -q tests/security` - passed
- `pytest -q tests/unit/test_pointer_address_resolution.py tests/unit/test_artifact_provenance_dag.py tests/unit/test_workflow_run_input_bindings.py` - passed
- `pytest -q tests/property/test_pointer_dual_write_consistency.py tests/property/test_provenance_projection_compatibility.py` - passed
- `pytest -q tests/runtime/test_approvals_artifacts_pointers_cli.py` - passed
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py` - passed
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py` - passed
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py` - passed

Additional targeted closure regression:
- `pytest -q tests/runtime/api/test_pointer_list_endpoint.py` - passed

Demo entrypoint verification:
- `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --db-url sqlite:///.tmp/strategy_a_strong_closure.db --scenario stage06_publish_ready --pilot-key strategy-a-strong-closure --output-root .tmp/strategy_a_strong_closure_artifacts --output-json .tmp/strategy_a_strong_closure_output.json` - passed
  - `workflow_run_id=wr-8f969884a3a0bc4445559ea9`
- `PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py --db-url sqlite:///.tmp/strategy_a_strong_closure.db --workflow-run-id wr-8f969884a3a0bc4445559ea9 --output .tmp/strategy_a_strong_closure_bundle.zip` - passed

## 5) Closure outcome vs acceptance criteria
1. Canonical pointer identity authoritative in writes/events/public/demo reads: **met**.
2. Legacy carriers compatibility-only: **met**.
3. Docs/schemas/runtime behavior aligned on canonical pointer identity semantics: **met**.
4. Demo/export from clean setup still operational: **met**.
5. Ready for monotone next tranche without reopening identity migration: **met**.

## 6) Residual compatibility debt (safe)
Remaining compatibility surfaces (intentional):
- CLI pointer read commands remain run-key shaped (`pointers show`, `pointers list`).
- `/api/v1/pointers?workflow_run_id=...` remains as compatibility alias filter.

Why safe:
- these are read adapters over the same canonical pointer rows/events.
- authoritative pointer writes and event payload identity no longer depend on legacy carrier semantics.
