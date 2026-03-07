You are a Codex coding agent working in this repo.

## GOAL
Finish **Strategy A / Strategy A′ strong closure** so the repo no longer relies on legacy run-local pointer identity as the canonical officialness substrate.

The current repo already has the Strategy A logical seam:
- `PointerAddress`
- `PointerId`
- provenance DAG capture
- exact input bindings
- scope-based pointer promotion checks
- demo/workspace/export compatibility fixes

But the substrate is still only **partially canonicalized**:
- `artifact_pointers` is still structurally keyed by `(workflow_run_id, pointer_key)`
- pointer repositories still center `get_pointer(workflow_run_id, pointer_key)` / `list_pointers_for_workflow_run(workflow_run_id)`
- `/api/v1/pointers` is still run-local in shape
- `artifact.pointer.promoted` still emits legacy `pointer_key` as `payload.pointer_id`
- multiple docs still describe run-local pointer identity as canonical

Your job is to finish the remaining closure **without breaking the current demo or run-centric compatibility views**.

This is a **strong-closure identity migration**. It is not a next-tranche feature task.

---

## WHY THIS TASK EXISTS
Strategy A is only fully complete when the authoritative officialness law is canonical end-to-end:

\[
\Pi:(tenant,domain,dataset,partition,stream?,registry\_kind)\rightharpoonup (artifact\_version,generation)
\]

with workflow run becoming provenance/governance context, not structural ownership of officialness.

At the moment, the repo is still in a mixed state:
- logical canonical seam exists,
- but storage/event/read contracts still carry legacy run-local identity.

The next tranche should build on a fixed substrate. Do not leave this half-finished.

---

## NON-GOALS
Do **not** implement the next tranche.
Do **not** introduce workflow-family/module/evaluator architecture here.
Do **not** weaken current governance-local checks in order to simplify the migration.
Do **not** remove run-centric compatibility views unless you replace them with tested compatibility projections.
Do **not** silently reinterpret history.
Do **not** guess ambiguous historical mappings.

If you discover a blocker that makes full strong closure unsafe, document it explicitly and stop at the maximum safe closure point.

---

## STEP 0 — READ CONTEXT IN THIS ORDER

### Operating rules / planning
- `AGENTS.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/TEST_STRATEGY.md`
- `docs/planning/TEST_MATRIX.md`

### Strategy A / closure docs
- `docs/planning/STRATEGY_A_CLOSURE_REPORT.md`
- `docs/architecture/promotion_semantics.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/vision/MATHEMATICAL_FOUNDATIONS.md`

### Core implementation surfaces
- `src/onetruth/domain/pointer_address.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/artifact_pointers.py`
- `src/onetruth/infrastructure/repositories/input_bindings.py`
- `src/onetruth/infrastructure/repositories/artifact_provenance.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/routes/pointers.py`
- `src/onetruth/api/routes/workflow_runs.py`
- workspace / export projection code used by the demo

### Tests most likely to matter
- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `tests/property/test_pointer_dual_write_consistency.py`
- `tests/property/test_provenance_projection_compatibility.py`
- `tests/unit/test_artifact_provenance_dag.py`
- `tests/unit/test_workflow_run_input_bindings.py`
- `tests/runtime/api/test_workflow_run_detail_contract.py`
- `tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `tests/runtime/test_realistic_schedule_planning_pilot.py`
- `tests/contract/test_schema_pointer_address_alignment.py`
- `tests/contract/test_runtime_db_schema_matches_models.py`
- `tests/integration/test_migration_bootstrap_parity.py`

---

## STEP 1 — CONFIRM BASELINE
Run and record:

- `make schema-validate`
- `python3 scripts/validate_repo.py --schemas-only`
- `pytest -q tests/contract/test_schema_pointer_address_alignment.py`
- `pytest -q tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`

Also run the canonical demo command from `docs/planning/STRATEGY_A_CLOSURE_REPORT.md`.

If baseline is not green, separate:
1. pre-existing unrelated failure,
2. real Strategy A strong-closure bug,
3. stale test still pinned to legacy semantics.

Do not blur these together.

---

## STEP 2 — WRITE TESTS FIRST
Before implementation, add or adapt tests to pin the strong-closure end state.

### Required coverage
1. canonical pointer identity is authoritative in storage and can be queried without `workflow_run_id`
2. legacy run-centric queries still work through compatibility adapters/views
3. `artifact.pointer.promoted` emits the canonical `PointerId` in payload and link identity
4. scope-based same-scope cross-run targets still work
5. out-of-scope targets still fail closed
6. governance-local approval checks still hold
7. workspace/export/run-detail demo surfaces still behave correctly
8. migration/bootstrap parity holds for fresh DB and upgraded DB
9. docs/schemas/model tests align with the new canonical truth

### Likely test work
- update tests that currently assert `payload.pointer_id == pointer_key`
- add repository tests for canonical get/list by pointer id/address
- add API tests for canonical pointer filters and compatibility workflow-run filters
- add migration parity tests if schema identity changes require them
- keep the demo-facing workspace/export tests intact as characterization suite

Prefer narrow, high-value regression tests over massive rewrites.

---

## STEP 3 — IMPLEMENT STRONG CLOSURE

### A. Make canonical pointer identity authoritative in storage
Refactor `artifact_pointers` so canonical officialness identity is authoritative.

Acceptable end states:
- primary key is canonical `pointer_id`, with compatibility uniqueness/indexes for legacy fields; or
- a canonical unique key over address columns is primary/authoritative, with stable `pointer_id` as externally visible identity.

In either case, the authoritative truth must no longer depend structurally on `(workflow_run_id, pointer_key)`.

Preserve:
- generation/CAS semantics
- auditability
- compatibility lookup paths where still needed

### B. Rework repositories around canonical identity
Add canonical repository surfaces such as:
- `get_pointer_by_id(...)`
- `get_pointer_by_address(...)`
- canonical list/query methods by tenant/domain/dataset/partition/stream/registry kind

Keep compatibility wrappers for run-centric callers, but make them adapters over the canonical implementation.

### C. Update authoritative commands and events
`promote_pointer_command` and related write paths must:
- operate against the canonical pointer identity
- emit canonical `payload.pointer_id`
- emit pointer subject links keyed by canonical pointer id
- keep exact input bindings and provenance capture correct under the new identity

Do **not** regress same-scope cross-run support or governance-local approval checks.

### D. Update public read surfaces
Rework `/api/v1/pointers` so canonical querying is the primary API shape.
Keep `workflow_run_id` as a compatibility filter if needed, but it must be clearly secondary.

Ensure run detail/workspace/export/read surfaces continue to work through compatibility projections.

### E. Finish docs/schemas alignment
Update docs and schemas so the repo has one truthful current description of pointer identity.
At minimum inspect and update:
- `docs/architecture/promotion_semantics.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- any runtime schema docs that still imply run-local canonical identity

Do not leave contradictory descriptions behind.

---

## STEP 4 — CREATE REQUIRED ANALYSIS ARTIFACT
Create a repo-native closure report, for example:

- `docs/planning/STRATEGY_A_STRONG_CLOSURE_REPORT.md`

It must include:
1. exact old-vs-new authoritative pointer identity law
2. files changed
3. migration strategy used
4. any compatibility adapters retained and why they are safe
5. any backfill or upgrade assumptions
6. exact demo command run and result
7. remaining debt, if any
8. explicit statement of whether Strategy A is now fully closed

If you encounter a blocker, document it precisely.

---

## STEP 5 — FULL VERIFICATION
Run and record all of the following, plus any new targeted tests:

- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/contract`
- `pytest -q tests/security`
- `pytest -q tests/unit/test_artifact_provenance_dag.py`
- `pytest -q tests/unit/test_workflow_run_input_bindings.py`
- `pytest -q tests/property/test_pointer_dual_write_consistency.py`
- `pytest -q tests/property/test_provenance_projection_compatibility.py`
- `pytest -q tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `pytest -q tests/runtime/api/test_workflow_run_detail_contract.py`
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`

Run the canonical demo/workspace export flow from clean setup and record it.

---

## ACCEPTANCE CRITERIA
Done means all of the following are true:

1. Authoritative pointer identity is no longer structurally run-local.
2. Canonical `PointerId` is emitted in authoritative events.
3. Canonical pointer query surfaces exist and are tested.
4. Compatibility run-centric surfaces still work.
5. Same-scope cross-run officialness continues to work.
6. Governance-local approval checks remain enforced.
7. Provenance DAG and exact input bindings remain correct.
8. Docs/schemas/model tests agree on the new truth.
9. Demo/workspace/export still run successfully.
10. Repo truthfully states that Strategy A is fully closed.

---

## DELIVERABLES
At the end, provide:

1. concise summary of what changed,
2. exact files changed,
3. exact tests/commands run,
4. path to the strong-closure report,
5. any remaining blockers or risks.
