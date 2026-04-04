---
id: TASK-0201
epic: EPIC-131
title: "Freeze clarified SME decisions and correct the boundary between schedule edits, route-demand edits, and accepted-series navigation"
status: DONE
owners: ["architect"]
reviewers: ["pm", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md"
  - "codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md"
patterns: []
---

## Why
The earlier operator-workpages packet encoded a materially wrong assumption: it treated schedule edits too much like route-demand edits. Before backend or frontend work continues, the repo needs one authoritative statement of the corrected SME boundary and one standard EPIC-131 entry surface for future fresh-session work.

## Scope
- import EPIC-131 into repo-native planning/context/task memory
- freeze the corrected workpage boundary across epic docs, context packs, and task briefs
- reconcile stale EPIC-125 status routing while touching repo memory
- record the accepted-series scope-key gap explicitly as a later backend task

## Out of scope
- runtime/API/frontend behavior changes
- preview/save endpoints
- frontend redesign
- `eod-v0` widening
- auto-agent rescheduling
- date-specific exceptions

## Repo-grounded findings frozen in this task
1. `schedule-v0` already has the correct bounded edit model because `draft_workbook.py` only allows `assigned_driver_id` and `assignment_status` edits.
2. The existing heatmap interaction already models same-day move/swap behavior that matches the clarified schedule request.
3. Route-demand examples already expose backend-owned daily buckets through `daily_demand_rows`, so later route-demand UX does not need frontend heuristics.
4. Artifact-backed schedule views still rebuild against latest run inputs, so pinned historical calculations are not yet safe.
5. Current repo review did not find a stable explicit artifact-level accepted-series grouping key on saved/published schedule artifacts.

## Frozen boundary
- `schedule-v0` = driver reassignment / on-call edits plus server recalculation only
- `route-demand-v0` = route-demand edits on a distinct truth object
- `driver-preferences-v0` = soft/advisory weekly snapshot
- accepted arrows = accepted history only
- draft lineage = separate from accepted history

## Source files changed
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md`
- `codex/context/EPIC-131.md`
- `codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md`
- `codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md`
- `codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md`
- `codex/tasks/TASK-0201-freeze-clarified-sme-decisions-and-correct-workpage-boundaries.md`
- `codex/tasks/TASK-0202-add-backend-workpage-descriptors-calculated-contract-blocks-and-accepted-series-queries.md`
- `codex/tasks/TASK-0203-implement-schedule-preview-recalculation-pinned-baselines-and-companion-calculation-evidence.md`
- `codex/tasks/TASK-0204-redesign-schedule-v0-frontend-for-live-heatmap-recalc-driver-metrics-and-version-rails.md`
- `codex/tasks/TASK-0205-implement-route-demand-v0-operational-editor-and-schedule-drift-propagation.md`
- `codex/tasks/TASK-0206-add-driver-preferences-v0-and-soft-advisory-integration.md`
- `codex/tasks/TASK-0207-close-epic-with-regressions-docs-compatibility-cleanup-and-deferred-item-markers.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`

## Verification
- `make schema-validate`
- `make contract`
- `rg -n "schedule-v0|route-demand-v0|driver-preferences-v0|accepted" docs/planning/epics/EPIC-131.md docs/planning/LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md codex/context/EPIC-131.md codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md codex/tasks/TASK-0201-freeze-clarified-sme-decisions-and-correct-workpage-boundaries.md codex/tasks/TASK-0202-add-backend-workpage-descriptors-calculated-contract-blocks-and-accepted-series-queries.md codex/tasks/TASK-0203-implement-schedule-preview-recalculation-pinned-baselines-and-companion-calculation-evidence.md codex/tasks/TASK-0204-redesign-schedule-v0-frontend-for-live-heatmap-recalc-driver-metrics-and-version-rails.md codex/tasks/TASK-0205-implement-route-demand-v0-operational-editor-and-schedule-drift-propagation.md codex/tasks/TASK-0206-add-driver-preferences-v0-and-soft-advisory-integration.md codex/tasks/TASK-0207-close-epic-with-regressions-docs-compatibility-cleanup-and-deferred-item-markers.md`

## Outcome
- EPIC-131 now has standard repo entrypoints under `docs/planning/epics/` and `codex/context/`.
- The corrected SME boundary is frozen in repo-native memory before any backend/frontend work continues.
- The accepted-series scope-key gap is explicit and delegated to `TASK-0202` instead of being silently inferred.
- Later EPIC-131 tasks now inherit one consistent schedule/route-demand/preferences/navigation model.
