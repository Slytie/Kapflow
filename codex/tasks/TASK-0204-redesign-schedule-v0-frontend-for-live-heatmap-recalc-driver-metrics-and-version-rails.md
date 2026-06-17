---
id: TASK-0204
epic: EPIC-131
title: "Redesign schedule-v0 frontend for live heatmap recalculation, driver metrics, compliance status, and version rails"
status: DONE
owners: ["frontend"]
reviewers: ["design", "qa"]
depends_on: ["TASK-0203"]
risk: high
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md"
  - "codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md"
patterns: []
---

## Context
The current schedule page renders the heatmap and several lower sections, but it does not yet provide the live operator feedback the SME requested.

## Objective
Rework `schedule-v0` so the page behaves like a calculated operator surface while staying bounded to schedule reassignment semantics.

## Non-goals
- No route-demand editing inside this page.
- No client-owned business logic for final calculations or compliance semantics.
- No generic spreadsheet runtime.

## Source files to read first
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`
- `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/types/workpages.ts`
- any frontend components for side panels / timeline / cards already reused elsewhere

## Source files to change
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`
- `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx`
- new shared or local components for:
  - top summary bar,
  - driver metrics table,
  - checks / validation panel,
  - version rails,
  - accepted-series arrow controls
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/types/workpages.ts`
- targeted frontend tests / snapshots

## Plan
1. Move the daily demand summary to a horizontal top bar and drive it from `calculations.top_bar`.
2. Add per-driver metrics columns/cards for hours, scheduled routes, and on-call shifts.
3. Surface compliance / capacity checks in a clearly readable validation area.
4. Trigger live preview recalculation after heatmap edits and use server-authored results to update the top bar, metrics, checks, and selected-day available-driver state.
5. Add available-driver count at top and optional green highlighting when a driver is both available and compliant.
6. Add clear version navigation with:
   - accepted-only top arrows,
   - separate side rails for accepted series and draft lineage,
   - clear visual distinction between draft and accepted state.
7. Keep save semantics explicit: preview updates the page state; save creates a new draft successor.

## Verification
- frontend interaction tests for heatmap move / swap + preview refresh
- tests proving accepted arrows never traverse drafts
- tests proving draft lineage and accepted series render separately
- tests proving page state refreshes after save

## Acceptance criteria
- Heatmap edits trigger live recalculation and update all required summary surfaces.
- The page displays driver metrics, compliance status, capacity posture, and available-driver cues.
- Accepted-version navigation and draft-version navigation are visibly separate.
- Save still creates immutable draft successors and refreshes the page to the new saved state.
