---
id: TASK-0253
epic: EPIC-139
title: "Operator home failure-state surface"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0243", "TASK-0252"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR020` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Production root/operator page shows current state plus missing seeds, stale edges, late reports, duplicate drift, missing blobs.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-011 plus regression tests
- Acceptance gate: `Root not /demo in shared_env; actor switching hidden; failure-state fixtures pass.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Root not /demo in shared_env; actor switching hidden; failure-state fixtures pass.
- Review focus covered: CR-011
- Refactor focus covered: RF-013
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR020`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR019;PR010`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Replaced the app-root demo redirect with a real `OperatorHomePage` at `/`.
- Added `GET /api/v1/operator/home`, scoped by server-derived request context, backed by the `logistics_reconciler_dry_run.v1` report.
- Extended the reconciler to report missing file-backed artifact blobs without exposing local blob paths in findings.
- Shared-env viewer sessions now render static identity posture; the actor-switcher affordance is hidden when `actor_switching_allowed=false`.
- Failure-state fixtures cover missing seed, missing blob, late report, and stale edge groups on the operator home surface.
- Evidence: focused backend operator-home/route-registry tests and frontend operator-home/viewer-bootstrap/root-route tests passed on 2026-06-02.
- Closeout posture: `MP-PR020` is closed as operator visibility and shared-env root hardening only; this is not CAPEX production activation, deployment approval, reconciler apply mode, or raw-corpus use.
