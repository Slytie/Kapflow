---
id: TASK-0148
epic: EPIC-124
title: "Implement backend workspace/stage-linked workpage action projection and generated snapshots"
status: DONE
owners: ["backend"]
reviewers: ["qa"]
depends_on: ["TASK-0147"]
risk: high
context_packs: ["codex/context/EPIC-124.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Once requirement/link semantics are safe, the backend still needs to project workpage actions onto the supported workspace/task/approval surfaces so the frontend stops inferring launch behavior.

## Objective
Add backend-projected workpage actions to the supported logistics workspace surfaces and generate backend-owned frontend snapshots for those contracts.

## Non-goals
- No frontend CTA rendering in this task.
- No broad workspace redesign.
- No new workpage kinds or finalization semantics.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/epics/EPIC-124.md`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

## Context packs / patterns to consult
- `codex/context/EPIC-124.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files to change
- `src/onetruth/api/routes/workflow_runs.py`
- supporting projection/actionability services as needed
- `src/onetruth/api/route_specs/` only if contract routing changes require it
- generated snapshot fixtures under `fixtures/frontend_contracts/`
- targeted runtime/API/snapshot tests
- task-memory / status docs as needed

## Generated / downstream artifacts impacted
- workspace/run-detail contracts with projected workpage actions
- backend-generated frontend snapshots for stage-linked workpage actions
- regression coverage for unavailable/available action states

## Plan
1. Project bounded workpage-action metadata on the supported workspace/task/approval surfaces.
2. Reuse canonical run-backed or artifact-backed routes in those actions rather than inventing new routes.
3. Fail unavailable actions truthfully when a supported surface cannot resolve a workpage route yet.
4. Generate and check backend-owned frontend snapshots in the same change set.

## Verification
- targeted runtime/API tests for workspace projection changes
- `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Supported logistics workspace surfaces now expose backend-projected workpage actions.
- The projected actions resolve to canonical run-backed or artifact-backed routes.
- Generated snapshots exist and remain distinct from human-authored workpage planning fixtures.
- No frontend-local inference is required for the supported CTA layer.

## Outcome
- `workflow_runs.py` now projects bounded `workpage_actions[]` onto supported workspace task and approval items while leaving graph nodes and unsupported surfaces unchanged.
- The backend now reuses shared canonical route helpers from `logistics_workpages.py` so workspace action routes, run-backed handoffs, and artifact submit responses share one route truth.
- Weekly schedule surfaces now truthfully project either an available `open_route` action or an unavailable `schedule_draft_unavailable` state based on the latest Stage04 draft artifact in the run.
- Dispatch-reporting Stage04 approvals now truthfully project either `create_draft_then_open` or `open_route` based on whether a compatible EOD draft already exists.
- Backend-owned frontend contract fixtures now include four new workspace-action snapshots for weekly available/unavailable and dispatch create/open states.

## Commands run
- `pytest -q tests/runtime/api/test_workspace_workpage_actions.py tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`

## Follow-ups
- `TASK-0149` should consume the projected `workpage_actions[]` contract directly instead of inferring launch behavior from task kind or artifact state.
- `TASK-0150` should close EPIC-124 by reconciling docs/status memory and recording the remaining known baseline caveats without broadening into new workpage families.
