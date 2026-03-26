---
id: TASK-0144
epic: EPIC-123
title: "Implement the frontend schedule artifact route, page, and landing handoff"
status: DONE
owners: ["frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0143"]
risk: high
context_packs: ["codex/context/EPIC-123.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0143`, the backend generic artifact-backed workpage family already supports the Stage04 schedule draft workbook. The frontend still needed to expose the canonical schedule artifact route, list the newest draft from the run-backed landing page, and provide bounded edit/submit/history/download behavior inside that route family.

## Objective
Implement the frontend schedule artifact slice by:
- adding `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`,
- discovering the newest `planning.draft_weekly_schedule.workbook` from workflow-run artifact truth,
- rendering a dedicated artifact-backed schedule page with bounded row editing,
- and keeping submit/download/history/stale/conflict flows inside the canonical nested run-backed route family.

## Non-goals
- No demo schedule artifact route.
- No schedule draft-create mutation.
- No Stage06 publish or live-dispatch semantics.
- No generic spreadsheet editor/runtime.

## Source files changed
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`
- `frontend/src/test/api/handlers.ts`
- `frontend/src/lib/api/onetruthApi.workpages.test.ts`
- `frontend/src/lib/repositories/workpagesRepository.test.ts`
- `frontend/src/pages/logisticsScheduleWorkpagePage.test.tsx`
- `frontend/src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx`
- `frontend/src/pages/logisticsWorkpageRoutes.test.tsx`

## Plan
1. Extend the frontend repository/API seam to fetch, submit, list history for, and download schedule artifact-backed workpages.
2. Add the canonical nested schedule artifact route and page component.
3. Make the run-backed schedule landing discover the newest draft workbook artifact from workflow-run artifact listing.
4. Cover landing-to-artifact handoff, submit lineage, history reopen, conflict reopen, and download flows in frontend tests.

## Verification
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx`

## Acceptance criteria
- The canonical route `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId` is active.
- The run-backed schedule landing now offers `Open editable draft` when the newest Stage04 draft workbook artifact exists for the run.
- The schedule artifact page supports bounded row edits, explicit submit, recent-history reopen, stale/conflict reopen, and JSON download.
- The frontend keeps demo schedule workpage discovery routed through the canonical run-backed landing rather than inventing a demo artifact alias.

## Outcome
- The schedule landing now discovers the newest Stage04 draft workbook artifact from workflow-run artifact truth.
- The frontend now has a dedicated canonical schedule artifact page under the run-backed workpage family.
- Schedule artifact submit, history, conflict reopen, and JSON download flows now stay inside the canonical nested route family.
- Frontend API, repository, MSW, and page tests now cover the schedule artifact-backed slice.

## Commands run
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx`

## Follow-ups
- `TASK-0145` closes EPIC-123 in status/docs/task memory and records the final route posture.
