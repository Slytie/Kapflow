# Strategy A current repo audit

## What I verified directly

I validated the updated repo with:

- `python3 scripts/validate_repo.py --schemas-only`
- `pytest -q tests/contract/test_schema_pointer_address_alignment.py`
- `pytest -q tests/unit/test_artifact_provenance_dag.py`
- `pytest -q tests/unit/test_workflow_run_input_bindings.py`
- `pytest -q tests/runtime/test_strategy_a_input_binding_capture.py`
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`

These passed in the inspected repo.

## What is clearly present

- canonical pointer-address seam in `src/onetruth/domain/pointer_address.py`
- typed provenance DAG repository support
- exact task/workflow input binding capture
- scope-based same-scope cross-run pointer-promotion allowance
- demo/workspace/export closure fixes for same-scope cross-run official outputs

## What is not fully closed yet

### 1. Storage identity is still run-local
`artifact_pointers` is still structurally keyed by `(workflow_run_id, pointer_key)` in:
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`

### 2. Repository identity is still run-local
`artifact_pointers` repository still centers:
- `get_pointer(workflow_run_id, pointer_key)`
- `list_pointers_for_workflow_run(workflow_run_id)`

### 3. Public pointer read surface is still run-local in shape
`src/onetruth/api/routes/pointers.py` still queries primarily by `workflow_run_id`, `scope_kind`, `scope_ref`, and `artifact_kind`, and does not expose canonical pointer querying as the primary contract.

### 4. Event payload identity is still legacy-shaped
`workflow_task_lifecycle.py` still emits:
- `payload.pointer_id = pointer_key`
for `artifact.pointer.promoted`.

### 5. Docs still conflict
Several docs still describe canonical pointer identity as run-local, including:
- `docs/architecture/promotion_semantics.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`

## Conclusion

The repo has **material Strategy A closure**, but not full strong closure.

The next safe step, if we want the substrate fully fixed before the next tranche, is to complete strong closure so that:
- canonical pointer identity is authoritative in storage,
- canonical pointer identity is authoritative in events,
- canonical pointer identity is authoritative in read contracts,
- legacy run-centric behavior becomes compatibility-only.
