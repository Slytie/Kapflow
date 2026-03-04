# Promotion semantics

Promotion is how mutable officialness is expressed without mutating immutable artifacts.

## 1) Authoritative promotion boundary

- Immutable artifacts live in `artifact_versions`.
- Officialness lives in audited pointer state (`artifact_pointers`) plus timeline events.
- Blob/object bytes are required evidence payloads but never decide officialness by themselves.

## 2) Promotion is distinct from approval

Approval evidence and pointer movement are separate canonical acts:
- approvals record whether a decision was authorized,
- promotion records which immutable artifact became official.

This separation is required for auditability, drift visibility, and replay.

## 3) Pointer identity, uniqueness, and generation

Promotion targets one canonical pointer stream per workflow-run scope:
- pointer key identity: `(workflow_run_id, pointer_key)`,
- pointer definition uniqueness: `(workflow_run_id, scope_kind, scope_ref, artifact_kind)`.

Generation semantics:
- first promotion creates generation `0`,
- repoint increments generation,
- repoint requires `expected_generation`,
- conflicting repoints fail closed (`pointer_conflict` / `pointer_generation_mismatch`),
- same-target repromotion is treated as no-op (`pointer_already_current`) and emits no new canonical effect.

## 4) Drift semantics

Drift is visibility-first:
- if reviewed artifact/version differs from promoted target, emit `artifact.pointer.drift_detected`,
- if reviewed Stage06 base differs from current base pointer during Stage07 promotion, emit drift event.

Drift does not silently mutate history and does not hide promotion; it is explicit event evidence.

## 5) Schedule Planning semantics

Schedule Planning has two official streams:
- Stage06 base publication (`schedule.published_schedule.workbook`),
- Stage07 major-replan deltas (`schedule.replan_delta.workbook`).

Rules:
- Stage06 base remains immutable after publication.
- Stage07 publishes additive immutable deltas; no in-place base edits.
- Stage07 official major replan promotion requires approved Stage07 approval evidence.
- Operative live-day schedule is reconstructed from base + ordered official deltas.

## 6) Lineage expectations for deltas

Stage07 delta artifacts must carry explicit lineage:
- `supersedes_artifact_version_id` for semantic replacement chain,
- metadata including `base_artifact_version_id` and `delta_sequence`.

Lineage and promotion events together must be sufficient to reconstruct order and investigate anomalies.

## 7) Idempotency expectations

Promotion commands require idempotency keys.

Required behavior:
- duplicate command idempotency does not create duplicate canonical effects,
- same-target retries stay non-duplicating,
- race losers fail closed and must retry against latest generation.

## 8) Minimum promotion event payloads

Promotion-related events must carry enough data for reconstruction/audit:
- pointer ID
- dataset key
- promoted artifact version ID
- reviewed artifact/base version ID when available
- workflow scope via envelope links
- drift reason for drift events
