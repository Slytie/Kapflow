# EPIC-030 - Artifact store + Promotion pointers + Drift visibility

## Summary
Define the artifact-store semantics that preserve immutable history while allowing explicit officialness and delta-based change.

## Why this epic exists
Artifact semantics are the practical expression of one truth. Without them, everything else drifts.

## Scope
### In scope
- artifact metadata schema
- pointer semantics
- drift visibility
- Schedule Planning base + delta design

### Out of scope
- advanced content diff rendering

## Dependencies
- EPIC-020
- EPIC-015

## Key decisions / constraints
- artifact contents are immutable; officialness lives only in audited pointer changes and ordered delta semantics
- Stage06 base publication may not be silently mutated by Stage07 live-day replans
- the operative live-day view must remain reconstructable from base + ordered deltas + promotion events
- reviewed version and promoted version may differ; drift must stay visible and attributable

Context pack: `codex/context/EPIC-030.md`

## Current Repo Status (2026-03-14)
- Completed in this epic: `TASK-0008`, `TASK-0009`, `TASK-0030`, `TASK-0081`, and `TASK-0097`.
- Shared/public HTTP artifact ingress now accepts request bytes only, while CLI/scenario/internal seeding remains available through canonical local-source-path ingress.
- Artifact and template download transport now also has sibling binary `.bin` routes with attachment headers, while the original JSON+base64 `/download` routes remain compatibility surfaces for current clients.
- Scope boundary remains unchanged: no object-store migration and no alternate attachment truth path were introduced in this tranche.

## Deliverables
- `schemas/artifacts/artifact_version_metadata.schema.json`
- `docs/architecture/promotion_semantics.md`

## Tasks
- TASK-0008
- TASK-0009
- TASK-0030
- TASK-0081
- TASK-0097
