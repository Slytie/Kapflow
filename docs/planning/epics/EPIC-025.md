# EPIC-025 - Canonical execution overlay + generated derivative policy

## Summary
Create the repo-native execution overlay that absorbs the useful CompanyOS method ideas without introducing a second authored workflow-definition system.

## Why this epic exists
Runbook packs and future generated IR need a canonical source. Without it, downstream materials will drift or become shadow truth systems.

## Scope
### In scope
- decision catalog files
- execution profile files
- schemas for both
- lowering / generation rules at the architecture level
- CI / test-matrix hooks for refinement and freshness

### Out of scope
- full runtime compiler implementation
- spec store
- generalized multi-level authored WorkflowSpec

## Dependencies
- EPIC-015

## Key decisions / constraints
- the execution overlay refines the workflow contract; it may not expand business semantics
- generated CompanyOS IR remains downstream of repo-native source
- `ExecutionSpec` is compiled and pinned per run; it is not a second authored workflow-definition surface
- generated artifacts should be written to a generated-output location, not mixed back into `docs/workflows/`

## Recommended pattern cards (read cards first)
- `PATTERN-001`
- `PATTERN-003`
- `PATTERN-005`

Context pack: `codex/context/EPIC-025.md`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

## Deliverables
- `docs/workflows/*/v1/DECISION_CATALOG.yaml`
- `docs/workflows/*/v1/EXECUTION_PROFILE.yaml`
- `schemas/agentic/*`
- `docs/architecture/EXECUTION_OVERLAY_MODEL.md`
- `docs/architecture/LOWERING_CONTRACT.md`

## Definition of Done
- both workflows have canonical decision and execution overlay files
- overlay schemas exist
- generated-derivative policy is explicit
- generated artifacts can be defined as downstream of repo-native source

## Current Repo Status (2026-03-08)
- Completed in this epic: `TASK-0020`, `TASK-0021`, `TASK-0024`, `TASK-0025`, `TASK-0032`, `TASK-0060`, `TASK-0061`, `TASK-0062`, `TASK-0063`.
- First logistics composition runtime coverage now includes:
  - `materialize_seed` weekly->live handoff (`TASK-0062`)
  - bounded first `notify_only` reporting->planning slice (`TASK-0063`)
- Later composition/observability expansions remain future tranche work.

## Tasks
- TASK-0020
- TASK-0021
- TASK-0024
- TASK-0025
- TASK-0032
- TASK-0060
- TASK-0061
- TASK-0062
- TASK-0063
