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

## Current Repo Status (2026-03-14)
- Completed in this epic: `TASK-0014`, `TASK-0015`, `TASK-0027`, `TASK-0044`, `TASK-0046`, `TASK-0047`, `TASK-0048`, `TASK-0049`, `TASK-0055`, `TASK-0056`, `TASK-0058`, `TASK-0064`, `TASK-0076`, `TASK-0083`, `TASK-0084`, `TASK-0085`, `TASK-0090`, `TASK-0091`, `TASK-0094`, `TASK-0095`, `TASK-0096`, `TASK-0098`, `TASK-0099`, `TASK-0100`.
- Primary operator/demo FE entrypoint is now `/demo/logistics`, powered by canonical backend story seam `GET /api/v1/stories/logistics-three-workflow`.
- Schedule-only board/workspace/runs/timeline surfaces remain available as legacy/internal regression paths and are explicitly labeled as legacy in navigation/UI copy.
- `TASK-0076` restored the legacy schedule-only board's compatibility with the current pointer-query contract without changing its board payload shape or promoting it back to a primary product surface.
- `TASK-0083` moved the shared HITL list-query seam into `src/onetruth/api/queries/` and added route-boundary contract coverage, while keeping the primary logistics story payload and the legacy board payload stable.
- `TASK-0084` made source/export bundle kinds explicit, added archive manifests for source and runtime workspace bundles, and taught repo validation to inspect a real exported release-bundle payload instead of trusting file-list assumptions.
- `TASK-0085` added a truthful local doctor path, honest lint/CI target boundaries, real CODEOWNERS coverage over existing roots, and explicit MIT/Node-version governance files without broadening into a heavier developer platform.
- `TASK-0090` closed the remaining bootstrap/install truth gap by aligning Python package metadata, CI/local editable installs, `.editorconfig`, frontend Node engines, and validator-enforced tracked build-artifact exclusion around one repo-authoritative toolchain story.
- `TASK-0091` added repo-native dependency automation, a dedicated secret-hygiene workflow, and explicit docs that secret revocation/history rewrite remain operator/admin follow-ups rather than routine code tasks.
- `TASK-0094` characterized the hand-rolled API shell and added a header-only `x-request-id` seam for future boundary telemetry, while keeping JSON payloads, route architecture, and event-correlation semantics unchanged.
- `TASK-0095` replaced the duplicated handwritten route matcher/dispatcher with a single declarative route registry, keeping the lightweight ASGI shell but centralizing route metadata, match order, and dispatch truth without changing payload or trust behavior.
- `TASK-0096` hardened the API boundary's JSON parsing contract with explicit route-aware body policies, deterministic `415`/`413` errors for wrong-media-type or oversize non-empty requests, and bounded larger envelopes for artifact-ingress routes without changing artifact semantics or trust behavior.
- `TASK-0098` migrated frontend/client download surfaces to the binary `.bin` transport, removed frontend dependence on JSON/base64 download envelopes, and made clean `npm ci` from the frontend lockfile the explicit install truth.
- `TASK-0099` split CI into parallel fast required lanes (`lint`, `contract`, `unit`, `security`) plus a separate `runtime-required` lane, moved `release-confidence` off pull requests, and kept `secret_hygiene` as its own PR-capable security workflow while retargeting `agent_api` to the fast backend aggregate.
- `TASK-0100` made `release_source_bundle` the only documented/operator-default shareable source artifact, added deterministic `release_provenance.json` sidecars to release exports, and demoted handoff/manual zip paths to internal-only review flows.
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
- TASK-0090
- TASK-0091
- TASK-0094
- TASK-0095
- TASK-0096
- TASK-0098
- TASK-0099
- TASK-0100
