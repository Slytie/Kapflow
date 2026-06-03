---
id: TASK-0139
epic: EPIC-122
title: "Implement the backend workflow-run-backed EOD landing/draft-resolution route and generated snapshot"
status: DONE
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
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
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

## Outcome
- The repo now exposes the canonical run-backed EOD landing route at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0` and the canonical run-backed draft-create route at `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`.
- The run-backed EOD landing response intentionally reuses the existing validated read-only EOD landing body, adds `run_context` plus `draft_resolution`, sets `source.mode=run_projection`, and keeps `artifact_context` absent so landing and editing remain clearly separated.
- Latest-draft resolution now selects the newest compatible `reporting.upd_draft.workbook` artifact inside the supplied reporting run and returns canonical `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` handoff routes without changing artifact-backed submit semantics.
- The canonical run-backed draft-create route now seeds the same immutable `reporting.upd_draft.workbook` artifact family inside the supplied `dispatch_reporting.v1` run, while the demo create alias remains unchanged as a compatibility entrypoint.
- Backend-owned frontend contract fixtures now include `fixtures/frontend_contracts/workpage_eod_v0_run_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_run_artifact_create_response.json`.
- Repo-memory now records `TASK-0139` as complete and moves the next EPIC-122 implementation focus to `TASK-0140`.

## Verification notes
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_run_eod_contract.py tests/runtime/api/test_workpages_artifact_eod_contract.py tests/runtime/api/test_workpages_run_schedule_contract.py tests/unit/test_api_route_registry.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `python3.11 scripts/validate_repo.py --schemas-only`

## Follow-ups
- `TASK-0140` is next: migrate the frontend to canonical `/runs/:workflowRunId/workpages/*` routes while preserving the explicit artifact-backed EOD handoff.
- `TASK-0141` should update demo/story drilldowns so the canonical run-backed workpage routes are discoverable without leaving docs/status stale.
