---
id: TASK-0129
epic: EPIC-120
title: "Implement the backend schedule demo workpage query route and generated contract snapshot"
status: DONE
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0128"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0128`, the repo has a frozen workpage query contract and route family. The schedule page already exists on the frontend, but its active data path is still local/example-backed.

## Objective
Add the first backend demo workpage query surface for the schedule page, backed by the weekly-planning normalized example sources, and generate a backend-owned contract snapshot for it.

## Non-goals
- No frontend page migration yet.
- No EOD route in this task.
- No submit/materialize semantics.
- No artifact-backed schedule path.
- Do not simply serve the hand-authored workpage fixture verbatim.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `docs/workflows/weekly_schedule_planning/v1/examples/*`
- `fixtures/logistics/workpages/schedule_workpage_v0_view_model_example.yaml`
- `src/onetruth/api/route_registry.py`
- `src/onetruth/api/routes/` and `src/onetruth/api/route_specs/`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

## Source files to change
- new backend route/route-spec files for workpages
- new backend service/query builder for schedule demo workpage payloads
- snapshot-export helper(s) and generated snapshot file(s)
- targeted route/contract tests
- docs/task-memory files touched by the new query surface
- the task file itself with outcomes and follow-ups

## Plan
1. Add the schedule demo workpage backend builder from weekly example sources.
2. Add `GET /api/v1/workpages/demo/schedule-v0`.
3. Add route/contract tests for the new endpoint.
4. Extend backend-owned snapshot export/check flows with a schedule workpage snapshot.

## Verification
- targeted runtime/API tests for the new route
- frontend snapshot export/check coverage for the new workpage snapshot
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The backend returns a stable schedule workpage contract for `schedule-v0`.
- The payload is built from the weekly example sources, not served directly from the hand-authored workpage YAML fixture.
- A backend-generated schedule workpage snapshot exists under `fixtures/frontend_contracts/`.
- No frontend page code is migrated yet in this task.

## Notes / decisions
Keep the schedule page explicitly on the weekly-planning side of the boundary. Selected-day preview is fine; semantically authoritative day-of dispatch editing is not.

## Source files changed
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `src/onetruth/api/route_registry.py`
- `tests/runtime/api/test_workpages_demo_schedule_contract.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `tests/unit/test_api_route_registry.py`
- `fixtures/frontend_contracts/workpage_schedule_v0_state.json`
- repo-native status/task-memory docs for `EPIC-120`

## Verification run
- `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_api_route_registry.py tests/runtime/api/test_workpages_demo_schedule_contract.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `PYTHONPATH=src python3.11 scripts/export_frontend_snapshots.py --check`
- `python3.11 scripts/validate_repo.py --schemas-only`

## Completion notes
- Added the first backend demo workpage query route at `GET /api/v1/workpages/demo/schedule-v0`.
- Built the payload from the weekly actual-ops normalized example pack through the schedule-control bundle builder instead of serving the hand-authored workpage YAML.
- Committed the first backend-generated workpage snapshot at `fixtures/frontend_contracts/workpage_schedule_v0_state.json`.
- Left frontend repository migration and EOD backend query work for `TASK-0130` and `TASK-0131`.
