# EPIC-131 - Schedule heatmap recalculation, route-demand separation, accepted-series navigation, and soft preferences

## Summary
Extend the bounded logistics workpage surface so the weekly schedule page behaves like a calculated operator surface without collapsing schedule truth, route-demand truth, and accepted-version navigation into one ambiguous editor.

This epic is intentionally bounded to:
- `weekly_schedule_planning.v1`
- `schedule-v0` as a driver reassignment and recalculation surface
- `route-demand-v0` as a separate route-demand editor
- `driver-preferences-v0` as a soft/advisory weekly snapshot

## Status
Active on 2026-04-04. `TASK-0201` is complete as the doc-only repo-truth freeze for the corrected SME boundary. `TASK-0202` is the next implementation tranche.

## Scope
### In scope
- backend-owned workpage descriptors for `schedule-v0`, `route-demand-v0`, and `driver-preferences-v0`
- calculated schedule contract blocks for dependencies, calculations, draft lineage, accepted series, and actions
- schedule preview/recalculation, pinned dependency baselines, and machine-readable calculation evidence
- accepted-history navigation that stays distinct from draft lineage
- a dedicated route-demand editor that creates immutable demand successors and propagates explicit schedule drift
- a dedicated driver-preferences snapshot surface that feeds schedule calculations as soft/advisory input

### Out of scope
- `eod-v0` widening into a route-demand or dispatch editor
- route-demand editing inside `schedule-v0`
- automatic agentic rescheduling when route demand changes
- date-specific driver exception modeling
- generic spreadsheet runtime ambitions

## High-level decisions
1. `schedule-v0` remains the bounded heatmap for moving routes between drivers and on-call positions; it does not become the route-demand editor.
2. `route-demand-v0` is the correct non-EOD operational surface for plus/minus route-demand changes.
3. `driver-preferences-v0` is a separate soft/advisory weekly snapshot, not a hidden mutable side store.
4. Accepted-version arrows are accepted-history only; draft lineage stays separate.
5. Saved schedule drafts need pinned dependency manifests and machine-readable calculated evidence tied to the saved draft version.
6. Route-demand changes create drift/rerun follow-up in v1; they do not auto-run the agent.

## Dependencies
- EPIC-123 (artifact-backed schedule draft lane)
- EPIC-124 (stage-linked workpage actions and requirement-aware linkage)
- EPIC-125 (first local operator demo and clarified SME feedback)
- EPIC-030 (artifact immutability, lineage, and pointer semantics)

## Recommended pattern cards (read cards first)
- none; stay repo-grounded to the current workpage, artifact, and schedule-control seams

Context pack: `codex/context/EPIC-131.md`

## Current repo status / rationale
- The current schedule draft editor already only mutates `assigned_driver_id` and `assignment_status`, so the existing edit model is aligned with route reassignment rather than route-demand editing.
- The current heatmap interaction in `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx` already models same-day move/swap behavior that matches the clarified SME request.
- Weekly route-demand examples already expose backend-owned daily buckets via `daily_demand_rows`, so day-level route-demand UX does not need frontend heuristics.
- Artifact-backed schedule views still rebuild against latest run inputs instead of a pinned saved baseline, which is unsafe once calculations, lineage, and accepted-history navigation matter.
- The current repo does not yet expose a stable explicit accepted-series grouping key on saved/published schedule artifacts; that remains a deliberate follow-on for `TASK-0202`.

## Tasks
- TASK-0201 - DONE
- TASK-0202 - TODO
- TASK-0203 - TODO
- TASK-0204 - TODO
- TASK-0205 - TODO
- TASK-0206 - TODO
- TASK-0207 - TODO

## Key decision
Do not solve the clarified SME request by stretching the existing workpages past their truth boundaries. Keep schedule reassignment, route-demand editing, advisory preferences, accepted history, and draft lineage explicit and separate.

## Red-team question
Are we still building one truthful workpage layer over canonical artifacts and calculations, or are we slipping back toward mixed truth objects, client-owned heuristics, and ambiguous version semantics?
