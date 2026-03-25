# EPIC-120 Context Pack - Logistics workpages v0

**Purpose (why you might open this):**
- You are implementing or extending the first logistics workpage FE surfaces.
- You need to keep the workpage slice aligned with the current primary `/demo/logistics` shell.
- You need to know which docs, examples, and product constraints are authoritative for schedule and end-of-day report pages.

## Non-negotiable invariants to keep in mind
- Workpages are **derived UI surfaces**, not a second truth model.
- The first tranche is **frontend-first** and **fixture-backed**.
- Do not invent a backend workpage API in the first FE slice.
- Do not retrofit the pages into the drawer model; these are full-page routes.
- Do not start from the legacy schedule-only FE routes.
- Keep the first scope to **schedule** and **end-of-day report** only.
- Keep the schedule page on the **weekly planning** side of the boundary; day-of replan belongs to `live_dispatch.v1`.
- Keep the EOD page on the **reporting draft/review** side of the boundary; do not anchor it to Stage05 final output semantics in v0.
- Update repo-native status/task/docs in the same change set when visible truth about this epic changes.

## Contracts / docs to treat as authoritative
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-120.md`
- `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_V0_PRODUCT_BRIEF.md`
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `docs/workflows/weekly_schedule_planning/v1/examples/*`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `docs/workflows/dispatch_reporting/v1/examples/*`
- `fixtures/frontend_contracts/README.md`
- `fixtures/logistics/workpages/*`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/lib/repositories/`
- `frontend/src/lib/types/workpages.ts`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`

## Required test coverage (tests-as-spec)
- view-model mapping tests for schedule and EOD example builders
- page render tests for both workpages
- interaction tests for bounded editable controls
- route integration tests proving the pages live under `/demo/logistics/workpages/*`
- doc/task-memory updates when routes/status/capability truth changes

## Current Repo Status (2026-03-25 implementation pass)
- The operator shell is route-based and repository-backed.
- `/demo/logistics` is the primary logistics surface.
- Existing task/action pages are drawer-first; workpages are the implemented full-page exception.
- The workpage repository/type surface exists as an example-backed frontend seam.
- There is no workpage HTTP contract yet.
- `AppShell` now treats `/demo/logistics/*` as logistics-shell routes.
- Workpage fixtures are human-authored planning/test artifacts and remain distinct from backend-owned `fixtures/frontend_contracts/` snapshots.

## Planned next work after this epic
- Backend projection of `(artifact_version, template) -> WorkpageViewModel`
- Backend submit/materialize flow for `(base_artifact_version, patch) -> new_artifact_version`

## Red-team questions for future runs
- Are we trying to solve artifact round-trip editing before the page contract is proven?
- Are we recreating raw spreadsheets instead of building guided operator pages?
- Are we adding new routes/components without updating page-map/status/capability docs?
- Are we quietly expanding this slice into live dispatch, a driver portal, or a fake backend API?
