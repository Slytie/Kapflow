# EPIC-120 Context Pack - Logistics workpages v0

**Purpose (why you might open this):**
- You are implementing or reviewing the logistics workpage slice.
- You need to know whether you are in the frontend-only validation tranche or the post-`TASK-0128` server-query tranche.
- You need to keep schedule and end-of-day report pages aligned with the current logistics workflow family without inventing a second truth path.

## Non-negotiable invariants to keep in mind
- Workpages are **derived UI/query surfaces**, not a second truth model.
- The first tranche validated the page contract with frontend-local example seams.
- The next tranche moves active pages onto **server-authoritative query contracts**.
- Do not jump straight into backend submit/materialize semantics in this batch.
- Do not retrofit the pages into the drawer model; these are full-page routes.
- Do not start from the legacy schedule-only FE routes.
- Keep the first scope to **schedule** and **end-of-day report** only.
- Keep the schedule page on the **weekly planning** side of the boundary; day-of replan belongs to `live_dispatch.v1`.
- Keep the EOD page on the **reporting draft/review** side of the boundary; do not anchor it to Stage05 final output semantics in v0.
- The schedule page is composite and must not be forced into one-artifact semantics too early.
- The EOD page is the better first future artifact-backed candidate.
- Update repo-native status/task/docs in the same change set when truth about this epic changes.

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
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
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
- backend route/contract tests for demo workpage query surfaces
- backend-generated frontend contract snapshot coverage for those routes
- frontend repository migration tests for workpage pages
- loading/error/freshness and route regression tests under `/demo/logistics/workpages/*`
- doc/task-memory updates when route/status/capability truth changes

## Current Repo Status (2026-03-25 post-`TASK-0131` frontend migration)
- `/demo/logistics/workpages/schedule-v0` and `/demo/logistics/workpages/eod-v0` exist as full-page routes.
- The active pages now read backend demo query contracts through the HTTP-backed repository seam.
- The post-v0 workpage query contract, route family, and snapshot policy are now frozen in repo-native docs.
- `GET /api/v1/workpages/demo/schedule-v0` and `GET /api/v1/workpages/demo/eod-v0` now exist as backend demo workpage routes.
- `fixtures/frontend_contracts/workpage_schedule_v0_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_state.json` now exist as backend-generated workpage query snapshots.
- Workpage pages now render local freshness/source metadata from the backend wrapper contract because the logistics shell hides the global shell freshness banner on `/demo/logistics/*`.
- Local form/checklist edits now survive refreshes when only `freshness.generated_at` changes.
- No artifact-backed workpage path exists yet.
- `fixtures/frontend_contracts/` remain backend-generated frontend API snapshots; future workpage query snapshots belong there too.
- Workpage planning fixtures remain distinct human-authored artifacts under `fixtures/logistics/workpages/`.

## Planned next work after this phase
- choose the next bounded tranche deliberately; `TASK-0131` completed the planned query-seam migration batch
- first artifact-backed EOD read/write path later, after a dedicated contract/task freeze

## Red-team questions for future runs
- Are we keeping active workpage pages on frontend-local data for too long instead of moving them onto server-owned queries?
- Are we quietly broadening the batch into submit/materialize semantics before the shared query seam is proven?
- Are we forcing schedule into one-artifact thinking when it is really a composite/run-oriented page?
- Are we confusing backend-generated API snapshots with the human-authored workpage planning fixtures?
