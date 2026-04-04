---
id: TASK-0205
epic: EPIC-131
title: "Implement route-demand-v0 operational editor and propagate route-demand changes into schedule drift"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0202"]
risk: high
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md"
  - "codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md"
  - "codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md"
patterns: []
---

## Context
The SME asked for plus/minus route adjustments on a non-EOD operational surface. This is a separate truth object from the schedule heatmap. It must update demand truth without turning the schedule page into the demand editor.

## Objective
Introduce `route-demand-v0` as the canonical operator surface for route-demand changes, and wire saved demand changes into schedule dependency drift / rerun follow-up.

## Non-goals
- No reuse of `eod-v0` as the primary route-demand solution.
- No automatic agentic re-scheduling.
- No direct mutation of existing schedule draft rows when route demand changes.

## Source files to read first
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/schedule_control/route_slot_requirements.py`
- `src/onetruth/application/services/schedule_control/bundle_builder.py`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`

## Source files to change
- backend workpage descriptor / route / handler files
- route-demand editor helpers under schedule-control or a dedicated workpage module
- workflow task / flag helpers for rerun follow-up
- frontend page/components for `route-demand-v0`
- relevant tests

## Plan
1. Add `route-demand-v0` run-backed and artifact-backed contracts over `planning.route_slot_requirements.workbook`.
2. Expose a clear plus/minus editing surface that stays backend-owned in how it maps day-level intent to slot-based demand rows.
3. Save immutable route-demand successor artifacts.
4. After save, evaluate the latest schedule draft baseline for dependency drift and create or reopen a rerun / refresh follow-up in the same workflow run.
5. Make run-backed schedule projections consume the latest route-demand artifact, while artifact-backed schedule views remain pinned to their own saved baseline.

## Verification
- route-demand workpage API tests
- tests proving route-demand saves create immutable successors
- tests proving route-demand changes mark schedule drafts drifted and surface rerun follow-up
- tests proving schedule artifact-backed views stay pinned while run-backed schedule entry reflects current demand

## Acceptance criteria
- Operators can adjust route demand on a dedicated non-EOD surface.
- Demand saves do not mutate schedule artifacts directly.
- Route-demand changes propagate into explicit schedule drift / rerun semantics.
- The schedule page consumes shared demand truth without duplicating it.
