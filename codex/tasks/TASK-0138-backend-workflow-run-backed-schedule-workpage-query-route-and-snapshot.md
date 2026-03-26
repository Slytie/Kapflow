---
id: TASK-0138
epic: EPIC-122
title: "Implement the backend workflow-run-backed schedule workpage query route and generated snapshot"
status: TODO
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0137"]
risk: high
context_packs: ["codex/context/EPIC-122.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0137`, the canonical run-backed route family is frozen. The next implementation tranche should make schedule the first run-backed workpage surface without forcing schedule into artifact-backed write semantics.

## Objective
Implement the backend workflow-run-backed schedule workpage query route and generate the backend-owned frontend snapshot for it.

## Non-goals
- No schedule write/materialize path.
- No EOD work in this task.
- No legacy workspace/task integration.
- No demo alias rewiring beyond what is required for backend truth.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/planning/epics/EPIC-122.md`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`
- any existing weekly-planning run/query helpers used by the demo shell or run detail surfaces

## Source files to change
- backend workpage route/route-spec files
- backend builder/service modules for run-backed schedule workpage projection
- targeted runtime/API tests
- snapshot export/check helper(s) and generated snapshot file(s)
- docs/task-memory files touched by the new route truth
- the task file itself

## Plan
1. Add the canonical run-backed schedule workpage route.
2. Build the contract from a real weekly schedule workflow run and its canonical source material.
3. Add targeted route/contract tests.
4. Export and check the backend-generated snapshot.

## Verification
- targeted runtime/API tests for the run-backed schedule workpage route
- `python3 scripts/export_frontend_snapshots.py --check`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The backend exposes the run-backed schedule workpage route.
- The payload is built from backend-owned run/source truth rather than serving a planning fixture verbatim.
- Missing or incompatible run context fails cleanly.
- A backend-generated snapshot exists for frontend consumption.

## Notes / decisions
Keep schedule explicitly query-backed/composite. If a missing run-side dependency appears, surface it as run/projection truth rather than hiding it behind demo defaults.
