# EPIC-131 Context Pack - Schedule heatmap recalculation, route-demand separation, and versioned workpage navigation

Purpose:
- You are extending the workpage surface after the first operator demo clarified that schedule reassignment, route-demand editing, accepted history, and soft preferences need to stay explicitly separate.
- You need to preserve one truthful workpage layer over artifacts, calculations, and lineage without widening into `eod-v0`, client-owned heuristics, or auto-rescheduling.

## Non-negotiable invariants to keep in mind
- Workpages remain derived surfaces; runtime rows, events, artifacts, pointers, and promotions remain canonical truth.
- `schedule-v0` edits only schedule assignment/on-call state plus server recalculation; it does not become the route-demand editor.
- `route-demand-v0` owns route-demand edits as a separate truth object.
- `driver-preferences-v0` is a soft/advisory snapshot, not a hidden mutable side store.
- Accepted history and draft lineage are separate concepts and must not share navigation semantics.
- Saved schedule drafts need pinned dependency baselines and companion calculation evidence; artifact-backed views must not silently recompute against latest run inputs.

## Contracts and docs to treat as authoritative
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md`
- `codex/context/EPIC-131.md`
- `codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md`
- `codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md`
- `codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Current repo status
- `src/onetruth/application/services/schedule_control/draft_workbook.py` already restricts schedule draft edits to `assigned_driver_id` and `assignment_status`.
- `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx` already models same-day move/swap heatmap behavior consistent with the clarified schedule request.
- `planning.route_slot_requirements.workbook` examples already expose backend-owned daily buckets via `daily_demand_rows`, so route-demand day editing does not need frontend heuristics.
- `src/onetruth/application/services/logistics_workpages.py` still rebuilds artifact-backed schedule views from current run inputs, so pinned historical calculations are not yet safe.
- Current repo review did not find a stable explicit artifact-level accepted-series scope key on saved/published schedule artifacts; that remains a deliberate follow-on in `TASK-0202`.

## Active implementation order inside this epic
1. `TASK-0201` - Freeze the corrected SME boundary and repo-native routing
2. `TASK-0202` - Add backend workpage descriptors, calculated contract blocks, and accepted-series queries
3. `TASK-0203` - Add schedule preview/recalculation, pinned baselines, and companion calculation evidence
4. `TASK-0204` - Redesign the schedule frontend around live recalculation and separate version rails
5. `TASK-0205` - Add `route-demand-v0` and explicit schedule drift propagation
6. `TASK-0206` - Add `driver-preferences-v0` and soft advisory integration
7. `TASK-0207` - Close the epic with regressions, docs, and deferred-item markers

## Smallest context set for the next task
- `docs/planning/LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md`
- `codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md`
- `codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md`
- `src/onetruth/application/services/schedule_control/draft_workbook.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx`

## Stop line
- No `eod-v0` widening.
- No route-demand truth inside `schedule-v0`.
- No auto-agent rescheduling from route-demand changes.
- No date-specific exception modeling in this epic.
- No client-owned slot-allocation or compliance logic.
