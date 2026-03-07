# Strategy A Strong-Closure Report

Date: 2026-03-07  
Scope: Strategy A / Strategy A' strong-closure identity migration.

## 1) Authoritative pointer identity law (old vs new)

Old authoritative storage law (legacy structural ownership):

\[
\Pi_{\text{legacy}}:(workflow\_run\_id,pointer\_key)\rightharpoonup (artifact\_version,generation)
\]

New authoritative storage law (canonical officialness substrate):

\[
\Pi:(tenant,domain,dataset,partition,stream?,registry\_kind)\rightharpoonup (artifact\_version,generation)
\]

Implementation realization in runtime storage:
- canonical row identity is `artifact_pointers.pointer_id` (primary key),
- canonical address fields (`tenant_id`, `domain_id`, `dataset_key`, `partition_kind`, `partition_key`, `stream_key`, `registry_kind`) are persisted on the pointer row,
- run-centric keys (`workflow_run_id`, `pointer_key`) are compatibility aliases, not structural ownership.

## 2) Files changed

- `alembic/versions/20260307_0008_pointer_identity_strong_closure.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/artifact_pointers.py`
- `src/onetruth/infrastructure/repositories/input_bindings.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/routes/pointers.py`
- `tests/unit/test_artifact_pointers_repository_canonical_identity.py`
- `tests/runtime/api/test_pointer_list_endpoint.py`
- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `tests/runtime/api/test_workflow_run_detail_contract.py`
- `tests/unit/test_workflow_run_input_bindings.py`
- `tests/contract/test_runtime_db_schema_matches_models.py`
- `tests/integration/test_migration_bootstrap_parity.py`
- `docs/architecture/promotion_semantics.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`

## 3) Migration strategy used

- Added Alembic revision `20260307_0008` to re-key `artifact_pointers` on `pointer_id`.
- Migration renames legacy table, creates canonical table with:
  - primary key `pointer_id`,
  - compatibility unique key `(workflow_run_id, pointer_key)`,
  - retained compatibility uniqueness `(workflow_run_id, scope_kind, scope_ref, artifact_kind)`.
- Data is copied forward (`INSERT ... SELECT ...`) without reinterpretation.
- Migration fails closed if any existing row has missing/blank `pointer_id`.

## 4) Compatibility adapters retained and why safe

Retained adapters:
- `get_pointer(workflow_run_id, pointer_key)` compatibility resolver.
- `list_pointers_for_workflow_run(workflow_run_id)` compatibility resolver.
- `/api/v1/pointers?workflow_run_id=...` compatibility filter.

Safety rationale:
- adapters now resolve through canonical scoped identity (`tenant/domain/partition`) and canonical pointer rows,
- they do not create a second authoritative path,
- canonical writes remain single-path (`pointer_id` stream + generation CAS),
- workspace/run-detail/export surfaces stay coherent in same-scope cross-run scenarios.

## 5) Backfill / upgrade assumptions

- Upgrade assumes existing pointer rows already have deterministic canonical `pointer_id`.
- If upgraded data contains null/blank `pointer_id`, migration exits with an explicit error and requires manual, deterministic backfill before retry.
- No ambiguous historical remapping is performed automatically.

## 6) Demo/workspace commands and results

Clean setup demo command:

```bash
PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py \
  --db-url sqlite:///.tmp/strategy_a_strong_closure_clean.db \
  --scenario stage06_publish_ready \
  --pilot-key strategy-a-strong-closure-clean \
  --output-root .tmp/strategy_a_strong_closure_clean_artifacts \
  --output-json .tmp/strategy_a_strong_closure_clean_output.json
```

Result:
- `status=ok`
- `workflow_run_id=wr-57126101c9dc10dd5685cae9`
- `reused_existing_run=false`

Companion export command:

```bash
PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py \
  --db-url sqlite:///.tmp/strategy_a_strong_closure_clean.db \
  --workflow-run-id wr-57126101c9dc10dd5685cae9 \
  --output .tmp/strategy_a_strong_closure_clean_bundle.zip
```

Result:
- `status=ok`
- bundle created at `.tmp/strategy_a_strong_closure_clean_bundle.zip`

## 7) Remaining debt

- `pointer_id` currently encodes canonical address (`tenant/domain/dataset/partition[/stream]`) while `registry_kind` remains an explicit canonical column; future format unification is optional and not required for Strategy A closure.
- CLI pointer read commands remain run-centric in input shape by design; canonical read shape is now primary on `/api/v1/pointers` and in repositories.

## 8) Strategy A closure status

Strategy A is **fully closed** for strong-closure identity migration criteria in this repo:
- authoritative pointer identity is no longer structurally run-local,
- canonical `PointerId` is emitted in authoritative pointer events and pointer links,
- canonical query surfaces exist and are tested,
- run-centric compatibility views are retained and tested as adapters.
