---
id: TASK-0115
epic: EPIC-100
title: "Establish an operability baseline with health/readiness and safe route/storage metrics"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0113"]
risk: medium
context_packs: ["codex/context/EPIC-100.md"]
patterns: ["PATTERN-008", "PATTERN-009"]
---

## Context
The repo now has structured boundary logs and request ids, but it still lacks the basic service-ops signals that make a first-user production lane comfortable to operate: health/readiness, route/storage metrics, and safe degradation visibility.

## Objective
Add the next observability layer needed for a stable first-user deployment without turning the repo into a telemetry platform or leaking sensitive data.

## Non-goals
- No full tracing platform rollout.
- No broad logging redesign.
- No secret or payload leakage into telemetry.

## Source files to read first
- `src/onetruth/api/main.py`
- `src/onetruth/api/boundary_logging.py`
- ops/degraded-mode docs
- storage/session modules for health signals
- relevant runtime/unit tests

## Context packs / patterns to consult
- codex/context/EPIC-100.md
- PATTERN-008
- PATTERN-009

## Source files to change
- health/readiness route or equivalent boundary surface
- safe metrics/signals implementation
- docs/ops guidance
- targeted tests

## Generated / downstream artifacts impacted
- operator docs and tests
- maybe small metrics helper modules if needed

## Plan
1. Define the smallest useful operability baseline for the current single-node system.
2. Add health/readiness and route/storage signals with safe field discipline.
3. Tie the signals back to the current degraded-mode and operator docs.
4. Freeze behavior with targeted tests.

## Verification
- targeted runtime/unit tests
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Operators can answer basic availability and degradation questions from repo-native signals.
- The repo gains metrics/health without turning observability into a second unbounded platform.
- No sensitive request or actor data is leaked.

## Notes / decisions
If a richer telemetry stack is needed later, it should build on this baseline rather than replace it blindly.

## Implementation notes
- Added internal JSON operator endpoints at `/api/v1/ops/health`, `/api/v1/ops/readiness`, and `/api/v1/ops/metrics` with explicit no-request-context / no-shell-DB-route handling in the thin API shell.
- Added a safe process-local request-metrics store plus non-mutating SQLite/artifact-root probes so readiness reflects actual operator-prepared substrate state instead of create-on-touch helpers.
- Tied degraded-mode visibility into readiness and metrics as warnings only, preserving the rule that derived-surface degradation does not redefine core substrate availability.

## Completion notes
- The repo now has a thin, repo-native operability baseline for first-user production without committing to Prometheus/OpenTelemetry, dashboards, alerts, or durable time-series storage.
- GitHub perimeter hardening remains the next bounded operator-facing gap in EPIC-100.
