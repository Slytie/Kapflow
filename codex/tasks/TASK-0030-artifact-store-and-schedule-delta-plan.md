---
id: TASK-0030
epic: EPIC-030
title: "Translate promotion semantics and schedule delta rules into artifact-store design"
status: DONE
owners:
  - platform
reviewers:
  - ops
  - security
  - qa
depends_on:
  - TASK-0008
  - TASK-0009
  - TASK-0023
  - TASK-0028
risk: high
context_packs:
  - codex/context/EPIC-030.md
patterns:
  - PATTERN-003
---

## Context
The docs define immutable artifact versions, audited pointers, drift visibility, and Schedule Planning base-plus-delta semantics, but they do not yet tell implementation code exactly how blob storage, metadata rows, pointer uniqueness, delta reconstruction, and promotion idempotency should work.

Current runtime status:
- TASK-0042 implemented canonical `artifact_versions` + `artifact_pointers` persistence and transactional event emission.
- TASK-0043 implemented first Stage06 publish-path usage of artifact version creation and pointer promotion.
- TASK-0045 implemented Stage07 issue-loop delta promotion and drift visibility on canonical runtime rows/events.
- TASK-0054 implemented realistic Schedule Planning pilot flows, including Stage07 delta usage for inspection.
- This task closes the remaining semantic gap: explicit artifact-store design closure for Stage07/base+delta reconstruction and blob adapter authority boundaries.

## Objective
Produce the remaining concrete artifact-store design for Stage 4: blob-store adapter contract, Stage07 delta promotion ordering, and base-plus-delta reconstruction semantics on top of the already-implemented canonical metadata/pointer substrate.

## Non-goals
- Do not build an advanced diff/merge UI.
- Do not re-open the one-truth decision that officialness lives in pointers/events rather than mutable files.
- Do not hide delta ordering in projection-only logic.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STAGE07_RUNTIME_MODEL.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- Stage06/Stage07 runtime handlers and pointer/artifact repositories
- Schedule Planning traces/scenarios covering publish/replan/drift

## Context packs / patterns to consult
- `codex/context/EPIC-030.md`
- `PATTERN-003`

## Source files to change
- `docs/planning/ARTIFACT_STORE_DESIGN.md` (new)
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `README.md`

## Generated / downstream artifacts impacted
- live-day schedule projections
- approval packets that bind to artifact snapshots
- lineage/export manifests
- generated runbook packs that explain publish/replan evidence

## Plan (completed)
1. Defined authoritative DB rows/events/pointers vs non-authoritative blob adapter behavior in `docs/planning/ARTIFACT_STORE_DESIGN.md`.
2. Specified pointer uniqueness/generation, supersedes lineage, Stage06 publish semantics, and Stage07 ordered-delta semantics.
3. Added explicit read-only reconstruction contract with required inputs, ordering rules, anomaly behavior, and inspectable metadata outputs.
4. Named concrete implementation test files and helper surfaces for base immutability, reconstruction, idempotency, drift, mismatch handling, superseded deltas, and approval-bound promotion.
5. Reconciled planning/architecture/status/task-memory docs so TASK-0030 is closed without stale wording.

## Verification
- the design makes it impossible to silently mutate the Stage06 base schedule
- the design makes it possible to reconstruct the operative live-day schedule from base + ordered deltas + promotion events
- pointer drift rules map back to `artifact.pointer.drift_detected`
- artifact officialness can be determined without reading mutable filesystem/object-store state alone
- full repo verification loop passes:
  - `make schema-validate`
  - `make contract`
  - `make replay`
  - `make acceptance`
  - `make runtime`
  - `pytest -q`

## Acceptance criteria
- artifact metadata, blob storage, and pointer rules are concrete enough for implementation
- Schedule Planning base and Stage07 delta semantics are fully specified
- promotion drift, idempotency, and reconstruction rules are explicit
- required tests and traces are named

## Notes / decisions
- Closed by adding `docs/planning/ARTIFACT_STORE_DESIGN.md` and aligned architecture/planning/status docs.
- The authoritative record remains metadata + timeline + pointers; blob storage holds immutable bytes but never decides officialness by itself.
