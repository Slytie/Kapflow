# EPIC-030 Context Pack — Artifact versions, pointers, drift, and Schedule Planning deltas

**Purpose (why you might open this):**

- You’re designing artifact persistence, pointer promotion, drift detection, or Schedule Planning base-plus-delta reconstruction.
- You’re deciding what is authoritative in blob storage versus database metadata and timeline events.

## Non-negotiable invariants to keep in mind
- Artifact contents are immutable; officialness changes only through audited pointers and ordered delta semantics.
- Stage06 publishes the stable base schedule; Stage07 must not mutate that base in place.
- The operative live-day view must be reconstructable from base + ordered deltas + promotion events.
- If the reviewed version differs from the promoted version, drift must be visible.

## Contracts / schemas to treat as authoritative
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `schemas/artifacts/artifact_version_metadata.schema.json`
- `schemas/artifacts/dataset_keys.yaml`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-003.md`

## Required test coverage (tests-as-spec)
- Immutability tests for artifact versions and pointer history.
- Drift visibility tests tied to `artifact.pointer.drift_detected`.
- Replay / acceptance checks for Schedule Planning happy path and drift-after-review traces.
- Property tests proving live-day reconstruction is possible from base + ordered deltas.

## Typical failure modes (red-team prompts)
- “Could the published base schedule be silently overwritten?”
- “Does the pointer move without enough evidence to reconstruct prior officialness?”
- “Can a delta become authoritative without a clear ordering and scope?”
- “Could orphaned blob storage become mistaken for official state?”

## Current Repo Status (2026-03-14)
- `TASK-0081` is complete:
  - shared/public HTTP artifact ingress accepts request bytes only,
  - CLI/scenario/internal local-source-path seeding remains on the same canonical artifact path,
  - no alternate attachment truth path was introduced.
- `TASK-0097` is complete:
  - artifact and template downloads now have sibling binary `.bin` routes that return bytes with attachment headers,
  - the existing `/download` JSON+base64 routes remain available as compatibility surfaces,
  - transport changed without reopening artifact metadata, pointer, provenance, or trust semantics.
