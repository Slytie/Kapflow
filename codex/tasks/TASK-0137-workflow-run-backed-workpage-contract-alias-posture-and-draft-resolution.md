---
id: TASK-0137
epic: EPIC-122
title: "Freeze the workflow-run-backed workpage route family, alias posture, and draft-resolution contract"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0136"]
risk: medium
context_packs: ["codex/context/EPIC-122.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0136`, the workpage layer had a complete demo/query baseline and a first artifact-backed EOD edit path. The next batch needed one explicit contract freeze for workflow-run-backed surfaces before backend or frontend migration work began.

## Objective
Freeze the canonical workflow-run-backed workpage route family, the relationship between demo aliases and canonical run-backed routes, and the minimal contract additions needed for run-backed schedule review plus EOD draft resolution.

## Non-goals
- No backend route implementation.
- No frontend route migration.
- No schedule write-path design.
- No EOD final-packet or approval semantics.
- No broad workspace/task integration design.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_BRIEF.md`
- `docs/planning/epics/EPIC-121.md`
- `docs/planning/epics/EPIC-122.md`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `docs/planning/FRONTEND_PAGE_MAP.md`

## Source files to change
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_BRIEF.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/CODEX_CONTEXT.yaml`
- task briefs and prompt/context files that need the frozen contract
- the task file itself

## Plan
1. Freeze the canonical backend route family for workflow-run-backed workpages.
2. Freeze the frontend alias/canonical route posture.
3. Decide the smallest contract extension for run context and EOD draft resolution.
4. Record the explicit stop line so later tasks do not reopen schedule writes or legacy workspace integration.

## Verification
- `python3.11 scripts/validate_repo.py --schemas-only`
- repo grep/check that EPIC-122 and `TASK-0137`..`TASK-0141` exist in epic/task/status memory and that the route-family decisions match across the plan, page-map, and HITL HTTP contract docs

## Acceptance criteria
- The repo has one explicit workflow-run-backed workpage route-family decision.
- The docs make the alias/canonical relationship explicit.
- The contract keeps schedule query-backed/composite and EOD artifact-backed editing distinct.
- `TASK-0138`..`TASK-0141` are unblocked without guesswork.

## Notes / decisions
Keep this task doc/contract-only. The goal is to eliminate ambiguity before backend/frontend work starts.

## Outcome
- EPIC-122 is now repo-native: the epic file, context pack, run-surfaces brief/plan, task briefs, and prompt pack all exist in the repo instead of only in an external handoff zip.
- The canonical backend workflow-run-backed family is now frozen as `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}` plus `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`, while the artifact-backed EOD read/submit routes remain unchanged.
- The canonical frontend posture is now frozen as `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`, with `/demo/logistics/workpages/*` retained as curated aliases until the run-backed routes are implemented and proven.
- The contract freeze keeps the existing workpage body/source/freshness envelope, adds optional `run_context` for run-backed surfaces, adds EOD-only `draft_resolution` for the run-backed landing page, and explicitly keeps `artifact_context` reserved for artifact-projection responses.
- Repo-memory no longer frames the next move as undecided: EPIC-122 is now the active next workpage package and `TASK-0138` is the next bounded implementation tranche.

## Verification notes
- `python3.11 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-122|TASK-0137|TASK-0138|TASK-0139|TASK-0140|TASK-0141" docs/planning/EPICS.md docs/planning/TASK_INDEX.md docs/status/CURRENT_FOCUS.md docs/status/DECISIONS_SINCE_LAST.md codex/CODEX_CONTEXT.yaml`

## Follow-ups
- `TASK-0138` is next: implement the backend run-backed schedule route and generated snapshot over canonical run/source truth.
- `TASK-0139` follows on the same frozen contract and can proceed in parallel only when the team uses isolated worktrees.
- `TASK-0140` should not start until the backend run-backed routes and snapshots exist.
- `TASK-0141` should remain the final user-visible drilldown/doc-sync tranche for this epic.
