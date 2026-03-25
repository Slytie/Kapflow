---
id: TASK-0128
epic: EPIC-120
title: "Freeze the post-v0 server-authoritative workpage query contract, route family, and snapshot policy"
status: DONE
owners: ["frontend", "backend"]
reviewers: ["qa"]
depends_on: ["TASK-0127"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
`TASK-0124`..`TASK-0127` established the first full-page logistics workpages as frontend-local/example-backed routes under `/demo/logistics/workpages/*`.

Before any backend route work starts, the repo needs one explicit post-v0 workpage query contract, route-family decision, and snapshot policy so backend and frontend converge on the same bounded seam.

## Objective
1. Freeze the post-v0 workpage query contract and route family.
2. Clarify how composite source metadata should be represented for schedule versus EOD.
3. Freeze snapshot policy so backend-generated workpage fixtures are not confused with human-authored planning fixtures.
4. Update repo-native task/status/docs memory so `TASK-0129`..`TASK-0131` can proceed without relying on the external zip bundle.

## Non-goals
- No backend route implementation yet.
- No frontend repository migration yet.
- No backend submit/materialize API.
- No artifact extraction/runtime yet.
- No generic template builder.
- No forced one-artifact model for the schedule page.

## Source files changed
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-120.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `fixtures/frontend_contracts/README.md`
- `codex/context/EPIC-120.md`
- `codex/tasks/TASK-0129-backend-schedule-demo-workpage-query-route-and-snapshot.md`
- `codex/tasks/TASK-0130-backend-eod-demo-workpage-query-route-and-snapshot.md`
- `codex/tasks/TASK-0131-http-backed-workpage-repository-migration-and-shell-regressions.md`
- the task file itself

## Verification
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The repo has one explicit post-v0 workpage query contract and route-family decision.
- The frozen contract does not assume a single `dataset_key` is enough for every page.
- Snapshot policy is explicit and does not blur planning fixtures with backend-generated contract fixtures.
- The task leaves `TASK-0129`..`TASK-0131` unblocked.

## Notes / decisions
The schedule page is composite and should not be forced into one-artifact semantics here. The first future artifact-backed path is expected to be EOD, not schedule.

## Implementation notes
- Froze the reserved route family around `GET /api/v1/workpages/demo/{workpage_id}` while explicitly reserving future artifact-backed and workflow-run-backed siblings.
- Froze a server-owned wrapper contract around the existing `WorkpageViewModel` with separate `source` and `freshness` metadata, including `primary_dataset_key` and `source_dataset_keys[]`.
- Clarified that backend-generated workpage query snapshots belong under `fixtures/frontend_contracts/`, while the human-authored workpage YAML fixtures remain planning/oracle artifacts under `fixtures/logistics/workpages/`.

## Completion notes
- `TASK-0129` and `TASK-0130` are now the next backend tranche for the schedule and EOD demo workpage query routes.
- `TASK-0131` remains gated on those backend routes and their generated snapshots.
