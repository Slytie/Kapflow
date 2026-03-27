---
id: TASK-0148
epic: EPIC-124
title: "Implement backend workspace/stage-linked workpage action projection and generated snapshots"
status: TODO
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
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
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
