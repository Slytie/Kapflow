---
id: TASK-0142
epic: EPIC-123
title: "Freeze the schedule draft artifact path, route family, and stage boundary"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0141"]
risk: medium
context_packs: ["codex/context/EPIC-123.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0141`, the canonical run-backed schedule landing page already exists, but the repo still needs one explicit contract freeze before any schedule artifact-backed implementation work starts.

The key ambiguity is no longer whether schedule should get a future artifact slice. It is where that slice starts and where it must stop.

## Objective
Freeze the first schedule artifact-backed workpage contract and route posture, including:
- the Stage04 draft workbook artifact family,
- the canonical landing versus artifact-route split,
- the explicit no-create-route decision,
- and the stop line that keeps Stage06 publish, Stage07 seeds, and live-dispatch edits out of scope.

## Non-goals
- No route implementation yet.
- No frontend page migration yet.
- No Stage06 publish or pointer semantics.
- No Stage07/live-dispatch editing.
- No generic spreadsheet editor/runtime.
- No broad workspace/human-task integration.

## Source files changed
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-123.md`
- `codex/context/EPIC-123.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_SCHEDULE_ARTIFACT_PATH_BRIEF.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_SCHEDULE_ARTIFACT_PATH_PLAN.md`
- `docs/domains/logistics/current-state/CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- the task file itself

## Plan
1. Add the new EPIC-123 planning/context package.
2. Freeze the Stage04 draft workbook as the first schedule artifact-backed family.
3. Freeze the canonical run-backed landing versus reserved artifact-route posture.
4. Record the no-create-route decision and explicit stop line in repo-native memory.

## Verification
- `python3.11 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-123|TASK-0142|planning\\.draft_weekly_schedule\\.workbook|schedule-v0/artifacts|schedule-v0/drafts" docs codex`

## Acceptance criteria
- The repo has one explicit contract/route-family decision for the first schedule artifact-backed slice.
- The contract keeps the edit surface on `planning.draft_weekly_schedule.workbook` rather than `planning.manager_review.doc`, Stage06, or Stage07 outputs.
- The contract does not invent `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`.
- The task leaves the first EPIC-123 implementation tranche unblocked.

## Notes / decisions
Keep this task doc/contract-only. The first schedule artifact slice should reuse the existing generic artifact-backed workpage family and the already-implemented run-backed schedule landing route rather than inventing a new draft-create seam.

## Outcome
- Added the repo-native EPIC-123 planning package for the first schedule artifact-backed workpage slice.
- Froze `planning.draft_weekly_schedule.workbook` as the first schedule draft-review artifact family and kept `planning.manager_review.doc` as evidence only.
- Reserved `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId` as the canonical future artifact route while keeping `/runs/:workflowRunId/workpages/schedule-v0` as the current landing page.
- Froze reuse of the existing generic `GET/POST /api/v1/workpages/artifacts/{artifact_version_id}` family for schedule artifact projection/submit.
- Made the no-create-route decision explicit: no first-slice `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts` because Stage04 already materializes the initial draft workbook.
- Recorded the stop line that keeps Stage06 published schedule, Stage07 daily seeds, live-dispatch day-of editing, generic editor scope, and broad workspace/task modernization out of this epic.

## Commands run
- `python3.11 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-123|TASK-0142|planning\\.draft_weekly_schedule\\.workbook|schedule-v0/artifacts|schedule-v0/drafts" docs codex`

## Follow-ups
- Queue the first EPIC-123 implementation tranche for backend schedule artifact projection/submit over `planning.draft_weekly_schedule.workbook`.
- After that, queue the frontend schedule artifact-route migration tranche and then the demo/doc closeout tranche.
