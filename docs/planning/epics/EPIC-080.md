# EPIC-080 - Ops readiness (CI/CD, dashboards, runbooks, generated checks)

## Summary
Stand up the operational checks needed to keep one truth system healthy as the platform grows.

## Scope
### In scope
- CI checks
- degraded-mode guidance
- runbook skeletons
- generated-artifact freshness checks
- full authored-surface validation and drift checks

## Dependencies
- EPIC-020
- EPIC-025

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-008`
- `PATTERN-009`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

Context pack: `codex/context/EPIC-080.md`

## Current Repo Status (2026-03-13)
- Completed in this epic: `TASK-0014`, `TASK-0015`, `TASK-0027`, `TASK-0044`, `TASK-0046`, `TASK-0047`, `TASK-0048`, `TASK-0049`, `TASK-0055`, `TASK-0056`, `TASK-0058`, `TASK-0064`, `TASK-0076`, `TASK-0083`, `TASK-0084`, `TASK-0085`.
- Primary operator/demo FE entrypoint is now `/demo/logistics`, powered by canonical backend story seam `GET /api/v1/stories/logistics-three-workflow`.
- Schedule-only board/workspace/runs/timeline surfaces remain available as legacy/internal regression paths and are explicitly labeled as legacy in navigation/UI copy.
- `TASK-0076` restored the legacy schedule-only board's compatibility with the current pointer-query contract without changing its board payload shape or promoting it back to a primary product surface.
- `TASK-0083` moved the shared HITL list-query seam into `src/onetruth/api/queries/` and added route-boundary contract coverage, while keeping the primary logistics story payload and the legacy board payload stable.
- `TASK-0084` made source/export bundle kinds explicit, added archive manifests for source and runtime workspace bundles, and taught repo validation to inspect a real exported release-bundle payload instead of trusting file-list assumptions.
- `TASK-0085` added a truthful local doctor path, honest lint/CI target boundaries, real CODEOWNERS coverage over existing roots, and explicit MIT/Node-version governance files without broadening into a heavier developer platform.
- Scope boundary remains unchanged: no second FE truth model and no generalized workflow-family UI framework was introduced in this tranche.

## Tasks
- TASK-0014
- TASK-0015
- TASK-0027
- TASK-0044
- TASK-0046
- TASK-0047
- TASK-0048
- TASK-0049
- TASK-0055
- TASK-0056
- TASK-0058
- TASK-0064
- TASK-0076
- TASK-0083
- TASK-0084
- TASK-0085
