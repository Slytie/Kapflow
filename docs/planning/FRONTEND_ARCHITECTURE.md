# FRONTEND_ARCHITECTURE.md

This document defines the frontend architecture for the HITL operator shell after real API integration.

## 1) Core posture
1. Frontend is a route-based SPA (`frontend/` React + TypeScript + Vite).
2. Server/runtime is authoritative for workflow/task/approval/flag/pointer semantics.
3. Client owns presentation state only:
   - URL-synced filters
   - drawer open/close
   - local selection/focus
   - safely replaceable optimistic visual affordances
4. Data layer is HTTP-backed through canonical HITL contracts (`/api/v1/*`).
5. API integration lives behind repositories so page/component composition is stable.
6. Refresh model is polling-friendly and explicit (`TanStack Query` intervals + `FreshnessBanner`).
7. No drag-to-transition semantics in v1.
8. Low-click expert workflow remains the primary UX objective.

## 2) Folder structure
```text
frontend/
  src/
    app/
      App.tsx
      AppShell.tsx
      useShellFilters.ts
    components/
      ActionCluster.tsx
      AttachmentActions.tsx
      ApprovalCard.tsx
      DetailDrawer.tsx
      FilterBar.tsx
      FlagCard.tsx
      FreshnessBanner.tsx
      LaneColumn.tsx
      PointerCard.tsx
      QueueRow.tsx
      SeverityChip.tsx
      StatePanel.tsx
      StatusBadge.tsx
      TaskCardWide.tsx
      TimelineRow.tsx
      workpages/
    pages/
      BoardPage.tsx
      MyWorkPage.tsx
      ApprovalsPage.tsx
      DispatchReportWorkpagePage.tsx
      ExceptionsPage.tsx
      LogisticsScheduleWorkpagePage.tsx
      RunsPage.tsx
      RunDetailPage.tsx
      OfficialOutputsPage.tsx
      TimelinePage.tsx
    lib/
      api/
        config.ts
        httpClient.ts
        idempotency.ts
        onetruthApi.ts
      repositories/
        workpagesRepository.ts
      workpages/
      mappers/boardLaneMapper.ts
      state/
      types/
        workpages.ts
    test/
      api/
        contractState.ts
        handlers.ts
        server.ts
```

## 3) Route map
- `/demo/logistics` -> primary three-workflow logistics shell plus canonical workpage launch point
- `/runs/:workflowRunId/workpages/schedule-v0` -> canonical weekly schedule landing page
- `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId` -> canonical artifact-backed weekly schedule editor/history page
- `/runs/:workflowRunId/workpages/route-demand-v0` -> canonical route-demand landing page
- `/runs/:workflowRunId/workpages/route-demand-v0/artifacts/:artifactVersionId` -> canonical artifact-backed route-demand editor/history page
- `/runs/:workflowRunId/workpages/driver-preferences-v0` -> canonical driver-preferences landing page
- `/runs/:workflowRunId/workpages/driver-preferences-v0/artifacts/:artifactVersionId` -> canonical artifact-backed driver-preferences editor/history page
- `/runs/:workflowRunId/workpages/eod-v0` -> canonical end-of-day landing page
- `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId` -> canonical artifact-backed end-of-day editor/history page
- `/board` -> board overview lanes (tasks/approvals/exception work)
- `/my-work` -> dense assigned queue with inline actions
- `/approvals` -> approval queue + review workspace split
- `/exceptions` -> flag/exception queue
- `/runs` -> workflow run list
- `/runs/:workflowRunId` -> workflow run detail tabs (timeline/tasks/approvals/artifacts/exceptions)
- `/official-outputs` -> pointer/current-official output view
- `/timeline` -> timeline explorer

## 4) Component boundaries
- Shell: `AppShell` (nav, top filter bar, freshness, drawer host).
- Route pages compose reusable components and repository hooks.
- Reusable low-click components own interaction surfaces, not business semantics.
- Descriptions remain drawer-first (`DetailDrawer`) and hidden on compact cards/rows.

## 5) Data-access boundary
- `httpClient` centralizes base URL, request headers, query serialization, and error normalization.
- `onetruthApi` maps canonical `/api/v1` endpoints to typed frontend contracts.
- Repositories expose route-ready interfaces:
  - `humanTasksRepository`
  - `approvalsRepository`
  - `flagsRepository`
  - `workflowRunsRepository`
  - `pointersRepository`
  - `timelineRepository`
  - `boardRepository`
- `workpagesRepository` (including canonical workpage create/preview/submit flows and recent-history filtering over workflow-run artifact lists)
- Components/pages do not call raw `fetch`.
- Workpage example builders may remain as oracle/test fixtures, but the active workpage routes now read backend canonical run/kind-scoped contracts through HTTP-backed repositories.

## 6) Polling and freshness model
- Pages use TanStack Query with bounded polling intervals.
- `FreshnessBanner` displays last successful refresh time and manual refresh affordance.
- Query invalidation is used after mutations to re-read authoritative state.
- No websocket/live-sync path in v1.
- Workpage pages now surface explicit page-local freshness/source metadata because `AppShell` intentionally hides the global shell freshness banner on `/demo/logistics/*`.

## 7) URL-synced filter strategy
- Search params encode `run`, `state`, `assignee`, `severity`, and `q`.
- `useShellFilters` + `urlFilters.ts` remain the only parse/serialize boundary.
- Filters are presentation-only and never override backend semantics.

## 8) Test strategy
- Component tests: inline actions, compact metadata, drawer behavior, attachment affordances.
- Route tests: board lanes, my-work filtering, approvals workspace, exceptions metadata, run detail tabs.
- Workpage tests: repository/API seam coverage, schedule/EOD page renders, logistics-shell preview/create entrypoints, refresh-preserved local edit interactions, submit/conflict/download behavior, and recent draft history/reopen behavior on the artifact-backed EOD route.
- Integration tests: claim/complete/respond round-trips, forbidden response handling, reload stability.
- Backend API contract tests verify `/api/v1` route contracts for board/list/detail/mutations.
- Workpage route tests should freeze both the page render behavior and the workpage query contract boundary.

## 9) Accessibility expectations
- Keyboard-operable interactive controls.
- Explicit button controls for transitions/affordances (no drag-only interactions).
- Drawer host has accessible close control and ARIA label.
- Status/severity signals include text (not color-only).

## 10) Workpage surfaces
- Canonical workflow-run-backed workpages live under `/runs/:workflowRunId/workpages/*`.
- Treat `/demo/logistics/*` as logistics-shell routes in `AppShell`.
- These pages are sibling full-page routes under `AppShell`, not children rendered inside `LogisticsDemoPage`.
- The current workpage layer uses canonical run-backed landing surfaces and artifact-backed editing/history surfaces.
- Example-backed builders remain oracle/test fixtures only; they are not the active route seam.
- `schedule-v0` stays on the weekly-planning review side of the boundary and offers reassignment/on-call edits plus server recalculation only.
- `eod-v0` stays on `reporting.upd_draft.workbook` / draft-review semantics and does not claim final-packet authority.
- `route-demand-v0` owns route-demand truth edits separately from `schedule-v0`.
- `driver-preferences-v0` is a soft/advisory weekly snapshot surface only.
- The logistics shell exposes canonical run-backed workpage links as the primary workpage entrypoints.
- The artifact-backed EOD route also reuses `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` for recent draft history instead of adding a new workpage-specific history endpoint.
- The schedule page is **composite** over multiple weekly-planning source datasets; future backend route design must leave room for run/composite projections and not assume one artifact per page.
- Active workspace action presentation is `open_route | create_then_open`.
- Human-authored workpage fixtures live under `fixtures/logistics/workpages/` and are distinct from backend-generated frontend contract snapshots in `fixtures/frontend_contracts/`.
