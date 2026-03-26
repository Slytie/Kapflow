---
id: TASK-0139
epic: EPIC-122
title: "Implement the backend workflow-run-backed EOD landing/draft-resolution route and generated snapshot"
status: TODO
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0137"]
risk: high
context_packs: ["codex/context/EPIC-122.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0137`, the run-backed route family is frozen. EOD already has an artifact-backed edit path, but it still needs a canonical run-backed landing/latest-draft-resolution route.

## Objective
Implement the backend workflow-run-backed EOD landing/draft-resolution route and generate the backend-owned frontend snapshot for it.

## Non-goals
- No changes to artifact-backed EOD submit semantics.
- No EOD final-packet or approval semantics.
- No schedule work in this task.
- No broad legacy workspace/task integration.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/planning/epics/EPIC-122.md`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `src/onetruth/infrastructure/repositories/artifact_versions.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

## Source files to change
- backend workpage route/route-spec files
- backend builder/service modules for run-backed EOD landing and latest-draft resolution
- targeted runtime/API tests
- snapshot export/check helper(s) and generated snapshot file(s)
- docs/task-memory files touched by the new route truth
- the task file itself

## Plan
1. Add the canonical run-backed EOD landing route.
2. Resolve the latest draft state for the workflow run without moving actual editing onto the landing route.
3. Add targeted route/contract tests.
4. Export and check the backend-generated snapshot.

## Verification
- targeted runtime/API tests for the run-backed EOD landing/draft-resolution route
- `python3 scripts/export_frontend_snapshots.py --check`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The backend exposes a run-backed EOD landing route.
- The route truthfully represents whether a draft exists and how to create/open it.
- The artifact-backed edit route remains the only place where actual workbook editing happens.
- A backend-generated snapshot exists for frontend consumption.

## Notes / decisions
Do not overload artifact-only metadata on a run-backed landing page if the page is not itself an artifact projection. Keep landing/resolution and editing clearly separated.
