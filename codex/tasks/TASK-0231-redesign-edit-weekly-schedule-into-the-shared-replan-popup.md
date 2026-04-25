---
id: TASK-0231
epic: EPIC-135
title: "Redesign Edit Weekly Schedule into the shared replan popup"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0228", "TASK-0229"]
risk: high
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: []
---

## Why
The operator should not have to switch between a weekly draft editor, separate day-of controls, and task-board scheduler launches. The popup needs to become the shared proposal-review and manual-override surface for both lifecycle lanes.

## Objective
Turn `Edit Weekly Schedule` into one shared popup shell that can render weekly-backed pre-publish proposals and live-dispatch-backed post-publish proposals above the existing heatmap/manual-edit surface.

## Non-goals
- replacing the heatmap editor itself
- contact-data authoring
- a second top-level workpage route family

## Source files to read first
- `frontend/src/app/AppShell.tsx`
- `frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx`
- `frontend/src/components/workpages/ScheduleWorkpageSurface.tsx`
- `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx`
- `frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx`

## Source files to change
- AppShell quick-edit modal wiring
- schedule popup/presentational components
- route-demand popup launch/handoff behavior
- frontend tests and backend snapshots/handlers that feed the popup

## Plan
1. Keep one popup shell but add proposal-first rendering:
   - canonical runtime status
   - proposed changes summary
   - top 3 picks
   - other eligible drivers
   - blocked candidates
   - phone numbers and compliance context
2. For brownfield repair, render proposed changes above the current schedule with `Apply` and `Ignore` actions.
3. For greenfield activation, open the popup immediately with canonical runtime status while the proposal is being built.
4. Keep the heatmap/manual-override surface below the proposal layer so operators can still choose their own edits.
5. Support stacked-modal launch when the flow begins from the route-demand popup, but implement it as one shared popup component over one contract rather than a second proposal system.
6. Migrate the primary Sick / No Show operator path into the shared proposal flow while keeping the direct action only as temporary compatibility fallback.

## Verification
- frontend tests for greenfield and brownfield popup rendering
- stacked-modal route-demand launch test
- tests proving top 3, all others, blocked candidates, phone numbers, and compliance metrics render correctly
- tests proving canonical runtime status is visible while proposals are building
- `npm --prefix frontend run typecheck`

## Acceptance criteria
- One popup handles weekly-backed and live-dispatch-backed deterministic replanning without waiting on the later live-dispatch runtime task.
- Brownfield proposals render above the existing schedule and can be applied or ignored.
- Operators can still make informed manual overrides with the same popup open.
