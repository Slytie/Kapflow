# ARTIFACT_STORE_DESIGN.md

Design-closure note for TASK-0030.

Purpose: lock implementation-ready semantics for artifact storage, pointer promotion, and Schedule Planning Stage06/Stage07 base-plus-delta reconstruction without introducing a second truth model.

## 1) Authority boundary: DB rows and timeline are authoritative, blob bytes are not

Authoritative runtime truth for artifacts is the combination of:
- immutable `artifact_versions` rows,
- immutable `timeline_events` entries (`artifact.version.created`, `artifact.pointer.promoted`, `artifact.pointer.drift_detected`),
- mutable audited `artifact_pointers` rows,
- explicit `artifact_links` attachment/linkage rows for subject binding.

Non-authoritative by itself:
- object/blob bytes referenced by `storage_uri`.

Implication:
- bytes can exist without becoming official,
- a blob is never official unless a canonical metadata row exists and the required event was committed,
- officialness changes only through pointer promotion in the same truth substrate.

## 2) Artifact version metadata rules

`artifact_versions` is append-only in effect: rows are inserted and never updated for business semantics.

Required row-level semantics:
- `artifact_version_id` is immutable identity.
- `workflow_run_id` scopes tenant/domain authority indirectly through workflow/run scope checks.
- `artifact_kind` must match workflow artifact-map keys.
- `storage_uri`, `content_digest`, and `byte_size` describe immutable bytes.
- `metadata_json` must be a JSON object and is immutable once stored.

Lineage metadata fields:
- `parent_artifact_version_id`: derivation/input lineage link.
- `supersedes_artifact_version_id`: semantic replacement relationship.
- `lineage_note`: human-readable lineage context (non-authoritative narrative aid).

Stage07 delta metadata requirements (implementation target):
- `base_artifact_version_id` (Stage06 base used during review),
- `delta_sequence` (strictly increasing integer for a workflow run and pointer stream),
- `flag_id` for issue-scoped deltas when a flag drove the replan.

## 3) Pointer uniqueness and generation semantics

Current canonical constraints:
- primary key `(workflow_run_id, pointer_key)`,
- uniqueness of pointer definition `(workflow_run_id, scope_kind, scope_ref, artifact_kind)`.

Meaning:
- one pointer key has one mutable target and one definition,
- one scope/kind stream cannot have two competing pointer keys.

Generation rules:
- first promotion inserts generation `0`,
- each repoint increments generation by `1`,
- repoint to a different target requires `expected_generation`,
- missing or stale generation fails closed (`pointer_conflict` / `pointer_generation_mismatch`),
- repoint to the same target is a no-op failure (`pointer_already_current`) and creates no new canonical effect.

## 4) Supersedes and lineage semantics

`supersedes_artifact_version_id` is authoritative lineage and must be used to model operational replacement intent.

Schedule Planning rules:
- Stage06 base publication artifact has no in-place mutation successor.
- Stage07 delta artifacts must use `supersedes_artifact_version_id` to reference the prior effective schedule node:
  - sequence 1 supersedes the published base, or
  - if prior official deltas exist, supersede the immediately prior effective delta.

`parent_artifact_version_id` remains optional derivation lineage and does not replace `supersedes` semantics.

## 5) Stage06 base publication semantics

Stage06 publishes a stable base schedule via:
1. immutable `artifact_versions` row for `schedule.published_schedule.workbook`,
2. approval response (`RESPONDED` + `approve`) when `promotion_reason=official_publish`,
3. pointer promotion to `official:schedule.published_schedule.workbook`,
4. authoritative `artifact.pointer.promoted` event.

Invariant:
- Stage06 base artifacts are immutable and never edited in place.
- New bases are new versions and explicit pointer moves.

## 6) Stage07 ordered-delta semantics

Stage07 does not overwrite the base schedule.
It publishes immutable deltas (`schedule.replan_delta.workbook`) and promotes them with explicit review/approval linkage.

Promotion gate:
- `promotion_reason=official_major_replan` requires `approved_by_approval_id`,
- approval must be same workflow run, `RESPONDED`, `response_kind=approve`,
- approval must be Stage07-scoped (`scope_ref=Stage07`).

Ordering rule:
- authoritative delta order comes from pointer-promotion event order for `official:schedule.replan_delta.workbook`,
- `delta_sequence` in metadata is required for deterministic replay/inspection and must be monotonic,
- mismatches between event order and `delta_sequence` are reconstruction anomalies, not silent behavior.

## 7) Live-day reconstruction semantics (base + ordered deltas)

Reconstruction is read-only and derived. It never mutates canonical rows.

Canonical equation:

`OperativeSchedule = Base(Stage06 pointer target) + ordered Stage07 official deltas`

### Read-only reconstruction contract (implementation target)

Surface shape (CLI/API/read service) must accept:
- `workflow_run_id` (required),
- `as_of_event_id` or `as_of_recorded_at` (optional; default latest),
- `base_pointer_key` (optional; default `official:schedule.published_schedule.workbook`),
- `delta_pointer_key` (optional; default `official:schedule.replan_delta.workbook`),
- `strict` (optional bool; default false).

Required output:
- `base_artifact_version_id`,
- ordered delta list with `artifact_version_id`, `delta_sequence`, `promoted_event_id`,
- `effective_tip_artifact_version_id` (latest applied delta or base),
- anomaly list (missing/superseded/stale/drifted),
- inspectable provenance (`promotion_event_ids`, `approval_ids`, `pointer_generations` when available).

Resolution rules:
1. Resolve base pointer target as-of snapshot.
2. Collect Stage07 delta promotions as-of snapshot from canonical events.
3. Resolve each promoted delta to `artifact_versions` metadata.
4. Order by:
   - `delta_sequence` (primary),
   - promotion event order (tie-break).
5. Apply lineage checks:
   - first delta must reference the resolved base in `supersedes_artifact_version_id` or `base_artifact_version_id`,
   - each subsequent delta should supersede the previous effective delta.
6. Emit anomalies instead of silently fixing order/lineage.

## 8) Drift detection semantics

Drift remains visibility-first and auditable:
- during promotion, if `reviewed_base_artifact_version_id` differs from the current base pointer target, emit `artifact.pointer.drift_detected`,
- if `reviewed_artifact_version_id` differs from promoted artifact version, emit drift event,
- promotion can proceed; drift is not silently ignored.

Operator/projection rule:
- drift events must be inspectable alongside promotions and approvals for the same workflow run.

## 9) Idempotent upload and idempotent promotion behavior

Upload/ingress idempotency:
- blob write is content-addressed (`sha256`) and path-stable,
- repeated writes of identical bytes are storage-idempotent (same digest path, no rewrite required),
- canonical artifact creation requires command `idempotency_key`,
- duplicate idempotency key must not create duplicate canonical rows/events.

Promotion idempotency:
- promotion command requires `idempotency_key`,
- duplicate idempotency key must not create duplicate `artifact.pointer.promoted` or drift events,
- same-target promotion with new key returns `pointer_already_current`,
- repoint races are serialized by generation checks; losing attempts fail closed.

## 10) Blob/metadata disagreement: failure and recovery expectations

Case handling:
- Blob exists, metadata missing:
  - treat as orphaned non-authoritative bytes,
  - safe to quarantine/delete by maintenance policy,
  - never infer official artifact state from orphaned bytes.
- Metadata exists, blob missing:
  - reads fail (`artifact_blob_not_found`),
  - pointer/event truth remains authoritative and inspectable,
  - remediation is re-ingest as a new immutable version and explicit repromotion if needed.
- Metadata digest does not match blob bytes (integrity check failure):
  - treat as corrupt blob equivalent to missing bytes,
  - flag anomaly in reconstruction output.

Recovery invariants:
- no backfill mutation of existing `artifact_versions` rows,
- remediation always creates new immutable versions and explicit pointer moves/events.

## 11) Required helper surfaces for implementation

The implementation tranche after this design closure should add:
- `src/onetruth/application/services/schedule_reconstruction.py`
  - `reconstruct_schedule_view(...)` read-only helper returning base, ordered deltas, and anomalies.
- `src/onetruth/infrastructure/repositories/artifact_promotions.py` (or equivalent query helper)
  - list pointer-promotion events for a workflow run/pointer key in authoritative order.
- thin read-only CLI/API boundary:
  - CLI example: `artifacts reconstruct-schedule --workflow-run-id ... --json`,
  - optional API example: `GET /api/v1/workflow-runs/{workflow_run_id}/schedule-reconstruction`.

No write-side behavior should be added to this read surface.

## 12) Required tests (named implementation targets)

Minimum tests that must be added in the implementation PR:
- `tests/runtime/test_artifact_store_base_immutability.py`
  - base artifact cannot be mutated in place; new base requires new version + pointer move.
- `tests/runtime/test_stage07_ordered_delta_reconstruction.py`
  - reconstruction returns deterministic base + ordered deltas.
- `tests/runtime/test_pointer_promotion_idempotency.py`
  - duplicate idempotency key and same-target promotions do not duplicate canonical effects.
- `tests/runtime/test_stage07_drift_visibility.py`
  - stale reviewed base emits `artifact.pointer.drift_detected` and remains inspectable.
- `tests/runtime/test_artifact_blob_metadata_mismatch.py`
  - missing/corrupt blob paths are surfaced as anomalies without changing canonical metadata truth.
- `tests/runtime/test_stage07_superseded_delta_handling.py`
  - superseded deltas are identified and excluded from effective chain (or flagged in strict mode).
- `tests/runtime/test_stage07_major_replan_approval_gate.py`
  - Stage07 official major replan promotion fails without approved Stage07 approval.

These tests are in addition to existing Stage06/Stage07 scenario and replay acceptance coverage.
