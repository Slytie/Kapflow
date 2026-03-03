# EPIC-015 - One truth system + authority model + vision preservation

## Summary
Freeze the single authority chain for the merged repo and preserve the philosophy / mathematics that explain why this architecture exists.

## Why this epic exists
Without an explicit authority model, the merger risks dual workflow-definition systems, stale generated artifacts, and loss of the deeper design rationale.

## Scope
### In scope
- authority model
- derivation / generation policy
- curated vision docs
- source-lineage mapping
- planning updates needed to remove stale assumptions

### Out of scope
- runtime implementation of spec storage or compiler pipeline
- ProcessPatch lifecycle

## Dependencies
- EPIC-000
- EPIC-005

## Deliverables
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/vision/*`
- planning and status updates

## Definition of Done
- a fresh contributor can distinguish authoritative source from generated / derived material
- no core doc implies a second peer truth system
- the CompanyOS philosophy and mathematics are preserved in repo-native docs

## Tasks
- TASK-0019
- TASK-0022
- TASK-0026
