# Strategy A' Closure Report (Post-Strategy 1 Cleanup)

Date: 2026-03-07  
Scope: Stabilization/closure pass for Strategy A' history-preserving substrate, with demo-facing compatibility verification.

## 1) Demo / pilot command(s) used

Canonical demo entrypoint (clean DB):

```bash
PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py \
  --db-url sqlite:///.tmp/post_strategy_closure_final.db \
  --scenario stage06_publish_ready \
  --pilot-key post-strategy-closure-final \
  --output-root .tmp/post_strategy_closure_final_artifacts \
  --output-json .tmp/post_strategy_closure_final_output.json
```

Companion export flow used by existing demo surface:

```bash
PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py \
  --db-url sqlite:///.tmp/post_strategy_closure_final.db \
  --workflow-run-id wr-8d36ff9cb6177aed545a5867 \
  --output .tmp/post_strategy_closure_final_bundle.zip
```

Result: both commands returned `status=ok`.

## 2) Legacy assumptions found before cleanup

- Workspace official-output projection in `api.workflow_runs.workspace` matched pointer targets only against run-local `artifact_versions`.
- After Strategy A' scope-based pointer promotion, same-scope cross-run pointer targets could exist, but workspace/export `official_outputs.outputs[].artifact_version` could become `null` despite a valid canonical target.
- Pointer promotion validation still had a stale run-local deny (`cross_workflow_artifact_reference`) instead of the intended governance-local + scope-based split.

## 3) What was cleaned up

- Replaced stale run-local artifact ownership check in authoritative pointer promotion with canonical scope validation:
  - allow same-scope cross-run artifact target,
  - deny out-of-scope target with explicit `artifact_scope_mismatch`,
  - preserve governance-local approval checks (`cross_workflow_approval_reference` still enforced).
- Added fail-closed guard for unresolved canonical pointer identity (`pointer_identity_unresolved`).
- Re-rooted workspace official-output projection to resolve scoped artifact targets by `artifact_version_id` + `tenant_id/domain_id` when target is not in run-local artifact list.
- Added/extended regressions to pin closure behavior:
  - pointer promotion same-scope cross-run allowed,
  - out-of-scope denied,
  - governance-local approval checks preserved,
  - workspace endpoint resolves cross-run scoped official output,
  - export bundle carries resolved official output for cross-run scoped pointer target.

## 4) Remaining transitional debt (contained)

- Legacy fields and read contracts remain in place intentionally (no reader cutover/backfill in this pass).
- API artifact list/detail payloads still center legacy shape; canonical fields are persisted and validated at authoritative write boundaries but not broadly exposed yet.
- Pointer address fallback logic remains, but unresolved identities are now fail-closed in authoritative promotion.

These are safe for next tranche because they do not introduce silent divergence in authoritative writes or demo-facing official output reads.

## 5) Drift status

- Canonical vs legacy drift in this closure scope: **quarantined to zero for new authoritative writes under tested flows**.
- No silent dual-read/dual-write masking found in demo-facing paths after cleanup.

## 6) Historical continuity guarantees

Verified live for new writes in tested paths:

- Typed provenance DAG compatibility edges are written.
- Exact workflow/task input bindings are captured when official state is consumed.
- Pointer/address semantics remain replay-compatible.

Evidence tests:

- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `tests/property/test_pointer_dual_write_consistency.py`
- `tests/property/test_provenance_projection_compatibility.py`
- `tests/unit/test_artifact_provenance_dag.py`
- `tests/unit/test_workflow_run_input_bindings.py`

## 7) Security split verification

Verified:

- Governance-local checks remain enforced (approval/run-local ownership where required).
- Scope-based state checks enforce tenant/domain/dataset/partition matching for pointer promotion targets.
- Same-scope valid access works; out-of-scope access fails closed.

Evidence tests:

- `test_pointer_promotion_allows_same_scope_cross_workflow_artifact_reference`
- `test_pointer_promotion_rejects_out_of_scope_cross_workflow_artifact_reference`
- `test_pointer_promotion_keeps_governance_local_approval_checks`
- `tests/security` suite

## 8) Next-tranche readiness

Status: **Ready for monotone extension**.

Rationale:

- Demo/pilot and export run clean from fresh setup.
- Demo-facing/public-facing read surfaces used by the pilot remain coherent with post-Strategy A' officialness semantics.
- Historical capture and scope/governance split are both enforced and test-pinned.

## 9) Blockers

None identified that should stop next-tranche implementation.

## Verification log (commands run)

- `make schema-validate`
- `python3 scripts/validate_repo.py` (`python` was unavailable in this environment)
- `pytest -q tests/contract`
- `pytest -q tests/security`
- `pytest -q tests/runtime/api/test_workflow_run_detail_contract.py`
- `pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`
- Additional closure checks:
  - `pytest -q tests/runtime/test_approvals_artifacts_pointers_cli.py`
  - `pytest -q tests/property/test_pointer_dual_write_consistency.py`
  - `pytest -q tests/property/test_provenance_projection_compatibility.py`
  - `pytest -q tests/unit/test_artifact_provenance_dag.py`
  - `pytest -q tests/unit/test_workflow_run_input_bindings.py`
