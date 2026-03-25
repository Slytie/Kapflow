---
id: TASK-0135
epic: EPIC-121
title: "Migrate the EOD page to the artifact-backed route with submit/conflict/download/version-lineage UX"
status: DONE
owners: ["frontend"]
reviewers: ["backend", "qa"]
depends_on: ["TASK-0134"]
risk: high
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0134`, the backend should expose artifact-backed EOD create/read/submit routes and generated snapshots. The frontend must now stop treating the EOD page as query-only once the operator chooses to create or open an editable draft.

## Objective
Add the artifact-backed EOD route and migrate the active editable EOD experience onto it, including explicit submit, conflict handling, download, and recent-version lineage UX.

## Non-goals
- No schedule write-path work.
- No generic builder/runtime abstraction.
- No final-packet semantics.
- No silent autosave to artifact versions.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- generated snapshots from `TASK-0134`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- the EOD page files/tests added by `TASK-0126` and `TASK-0131`

## Source files to change
- frontend API/repository files for artifact-backed EOD
- EOD page/components/tests for the artifact-backed route
- route wiring under `App.tsx` / `AppShell.tsx` if needed
- docs/task-memory files touched by visible route/data-source truth
- the task file itself with outcomes and follow-ups

## Plan
1. Add the artifact-backed EOD route under the logistics shell.
2. Reuse the validated page sections, but source/edit state from the artifact-backed backend contract.
3. Add explicit submit flow, conflict handling, download action, and recent-version lineage display.
4. Keep the query-backed EOD landing page as the entrypoint for creating or opening a draft.

## Verification
- frontend typecheck/build
- targeted route/repository/page tests for loading, submit success, conflict, download, and lineage
- snapshot/contract checks if relevant
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The active editable EOD experience is artifact-backed once a draft is opened.
- Submit navigates to or refreshes on the new superseding artifact version.
- The user can download the workbook artifact from the page.
- Schedule remains untouched except for shared infra if truly necessary.

## Notes / decisions
Keep local dirty/edit state on top of the fetched base contract, but let the server remain authoritative for validation/write decisions.

## Outcome
- `/demo/logistics/workpages/eod-v0` now remains the query-backed landing page, but renders as a read-only preview with a `Create editable draft` action.
- `/demo/logistics/workpages/eod-v0/artifacts/:artifactVersionId` is now the active editable EOD surface and reuses the existing section/field contract while loading from the artifact-backed backend route family added in `TASK-0134`.
- The artifact-backed page now supports submit, stale-artifact conflict reopen flow, workbook download through the normal artifact binary route, and bounded lineage visibility using `artifact_context`.
- Shared workpage frame/form/checklist components now support query-backed preview mode and artifact-backed action mode without changing schedule behavior.

## Verification notes
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx`
- `npm --prefix frontend run typecheck`
- `python3 scripts/validate_repo.py --schemas-only`

## Follow-ups
- `TASK-0136` remains the next bounded tranche for explicit demo entrypoints and richer version-history/reopen discovery beyond the minimal lineage controls added here.
