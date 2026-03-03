---
id: TASK-0030
epic: EPIC-030
title: "Translate promotion semantics and schedule delta rules into artifact-store design"
status: IN_PROGRESS
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
- Remaining gap for this task is the explicit Stage07 base-plus-delta reconstruction design and blob adapter behavior.

## Objective
Produce the remaining concrete artifact-store design for Stage 4: blob-store adapter contract, Stage07 delta promotion ordering, and base-plus-delta reconstruction semantics on top of the already-implemented canonical metadata/pointer substrate.

## Non-goals
- Do not build an advanced diff/merge UI.
- Do not re-open the one-truth decision that officialness lives in pointers/events rather than mutable files.
- Do not hide delta ordering in projection-only logic.

## Source files to read first
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/architecture/promotion_semantics.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `schemas/artifacts/artifact_version_metadata.schema.json`
- `schemas/artifacts/dataset_keys.yaml`
- Schedule Planning traces covering publish/replan/drift

## Context packs / patterns to consult
- `codex/context/EPIC-030.md`
- `PATTERN-003`

## Source files to change
- `docs/planning/ARTIFACT_STORE_DESIGN.md` (new)
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/architecture/promotion_semantics.md` if clarifications are required
- relevant traces/tests if new artifact invariants must be proven
- runtime artifact repositories under `src/onetruth/infrastructure/artifacts/` once implementation starts

## Generated / downstream artifacts impacted
- live-day schedule projections
- approval packets that bind to artifact snapshots
- lineage/export manifests
- generated runbook packs that explain publish/replan evidence

## Plan
1. Define the authoritative database rows for artifact versions and pointers, and the non-authoritative blob-store adapter contract.
2. Define pointer uniqueness, supersedes relations, and drift detection rules.
3. Define Schedule Planning base publication and ordered-delta reconstruction.
4. Define idempotent upload/promote behavior and the tests that prove it.

## Verification
- the design makes it impossible to silently mutate the Stage06 base schedule
- the design makes it possible to reconstruct the operative live-day schedule from base + ordered deltas + promotion events
- pointer drift rules map back to `artifact.pointer.drift_detected`
- artifact officialness can be determined without reading mutable filesystem/object-store state alone

## Acceptance criteria
- artifact metadata, blob storage, and pointer rules are concrete enough for implementation
- Schedule Planning base and Stage07 delta semantics are fully specified
- promotion drift, idempotency, and reconstruction rules are explicit
- required tests and traces are named

## Notes / decisions
The authoritative record is metadata + timeline + pointers. Blob storage holds immutable bytes but does not by itself decide what is official.
