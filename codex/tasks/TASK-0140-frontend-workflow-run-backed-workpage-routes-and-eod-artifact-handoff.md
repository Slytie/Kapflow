---
id: TASK-0140
epic: EPIC-122
title: "Migrate the frontend to workflow-run-backed workpage routes while preserving artifact-backed EOD editing handoff"
status: DONE
owners: ["frontend"]
reviewers: ["backend", "qa"]
depends_on: ["TASK-0138", "TASK-0139"]
risk: high
context_packs: ["codex/context/EPIC-122.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0138` and `TASK-0139`, the backend should expose canonical workflow-run-backed schedule and EOD workpage routes plus generated snapshots. The frontend must now move active usage from demo-only routes to the canonical run-backed routes.

## Objective
Add workflow-run-backed frontend routes and repositories, preserve the validated workpage UI, and keep artifact-backed EOD editing as a clear handoff from the run-backed landing route.

## Non-goals
- No schedule write path.
- No changes to artifact-backed EOD submit semantics.
- No new app root.
- No broad workspace/task integration.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- generated snapshots from `TASK-0138` and `TASK-0139`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- current workpage pages/components/tests

## Source files to change
- frontend API/repository files for run-backed workpage routes
- route wiring under `App.tsx` / `AppShell.tsx`
- workpage pages/components/tests for run-backed schedule/EOD usage and artifact-backed EOD handoff
- docs/status/page-map/capability/task-memory files touched by the new route truth
- the task file itself

## Plan
1. Add the canonical run-backed frontend routes under `/runs/:workflowRunId/workpages/*`.
2. Migrate the active schedule and EOD landing pages to those routes.
3. Preserve the artifact-backed EOD edit lane as the explicit next step from the run-backed landing route.
4. Add route/repository tests for loading, errors, and handoff behavior.

## Verification
- `npm --prefix frontend run typecheck`
- targeted frontend tests for run-backed workpage pages/repository/routes
- snapshot/contract checks if relevant
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Canonical run-backed frontend routes exist and use HTTP-backed repository data.
- Schedule and EOD landing pages load from workflow-run-backed backend routes.
- EOD artifact-backed editing remains a distinct explicit route/transition.
- Demo aliases still work or redirect truthfully while canonical routes are introduced.

## Notes / decisions
Do not silently reinterpret backend contracts in frontend code. If the contract is wrong, fix it in the backend/docs rather than hiding the mismatch.

## Implementation outcome
- Added canonical frontend routes at `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`.
- Extended the frontend workpage contract/API/repository seam to preserve backend `run_context` and `draft_resolution` without inventing a second local schema.
- Reused the existing schedule/EOD/artifact-backed pages as route-aware pages so canonical run-backed usage and demo aliases share the same validated UI.
- Kept `/demo/logistics/workpages/*` working as compatibility aliases while the canonical run-backed pages became first-class.
- Corrected artifact-backed submit/conflict route truth so canonical nested `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` paths are returned once the run-backed frontend is active.

## Commands run
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsWorkpageRoutes.test.tsx src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsDemoPage.test.tsx`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `python3.11 scripts/validate_repo.py --schemas-only`

## Follow-ups
- `TASK-0141` should rewire demo-shell/story drilldown entrypoints toward the canonical `/runs/:workflowRunId/workpages/*` surfaces and keep the alias posture/documentation truthful.
