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
    pages/
      BoardPage.tsx
      MyWorkPage.tsx
      ApprovalsPage.tsx
      ExceptionsPage.tsx
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
      mappers/boardLaneMapper.ts
      state/
      types/
    test/
      api/
        contractState.ts
        handlers.ts
        server.ts
```

## 3) Route map
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
- Components/pages do not call raw `fetch`.

## 6) Polling and freshness model
- Pages use TanStack Query with bounded polling intervals.
- `FreshnessBanner` displays last successful refresh time and manual refresh affordance.
- Query invalidation is used after mutations to re-read authoritative state.
- No websocket/live-sync path in v1.

## 7) URL-synced filter strategy
- Search params encode `run`, `state`, `assignee`, `severity`, and `q`.
- `useShellFilters` + `urlFilters.ts` remain the only parse/serialize boundary.
- Filters are presentation-only and never override backend semantics.

## 8) Test strategy
- Component tests: inline actions, compact metadata, drawer behavior, attachment affordances.
- Route tests: board lanes, my-work filtering, approvals workspace, exceptions metadata, run detail tabs.
- Integration tests: claim/complete/respond round-trips, forbidden response handling, reload stability.
- Backend API contract tests verify `/api/v1` route contracts for board/list/detail/mutations.

## 9) Accessibility expectations
- Keyboard-operable interactive controls.
- Explicit button controls for transitions/affordances (no drag-only interactions).
- Drawer host has accessible close control and ARIA label.
- Status/severity signals include text (not color-only).
