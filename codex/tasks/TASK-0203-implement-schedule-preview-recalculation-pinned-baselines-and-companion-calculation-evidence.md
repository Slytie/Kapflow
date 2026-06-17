---
id: TASK-0203
epic: EPIC-131
title: "Implement schedule preview recalculation, pinned baselines, and companion calculation evidence"
status: DONE
owners: ["backend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0202"]
risk: high
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md"
  - "codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md"
patterns: []
---

## Context
The current schedule draft flow can save a successor workbook, but it does not yet behave like a proper calculated workpage. The SME requests require immediate preview, visible compliance posture, and historically correct saved evidence.

## Objective
Turn `schedule-v0` into a calculated draft editor by adding:
- a preview/recalculation endpoint or action,
- pinned dependency baseline manifests,
- machine-readable calculation snapshot companions,
- companion evidence rematerialization on save,
- and dependency-drift guards for submit/publish.

## Non-goals
- No route-demand UI editing in this task.
- No driver-preferences page in this task.
- No automatic agentic re-scheduling.

## Source files to read first
- `src/onetruth/application/services/schedule_control/draft_workbook.py`
- `src/onetruth/application/services/schedule_control/bundle_builder.py`
- `src/onetruth/application/services/schedule_control/validation.py`
- `src/onetruth/application/services/schedule_control/route_slot_requirements.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/handlers/approvals.py`

## Source files to change
- `src/onetruth/application/handlers/workpages.py`
- new calculation / manifest helpers under `src/onetruth/application/services/schedule_control/`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/handlers/approvals.py`
- any artifact repository helpers needed for companion lookup / provenance
- targeted runtime and API tests

## Generated / downstream artifacts impacted
- `planning.draft_weekly_schedule.workbook`
- `planning.validation_summary.doc`
- `planning.draft_weekly_schedule.doc`
- new `planning.schedule_calculation_snapshot.json` companion
- schedule artifact-backed contracts
- weekly publish behavior

## Plan
1. Add a deterministic schedule preview calculation path that accepts unsaved row / reserve-row edits and returns:
   - top-bar day summaries,
   - per-driver hours / routes / on-call metrics,
   - compliance and capacity checks,
   - selected-day available-driver counts and IDs,
   - optional soft-preference hints.
2. Record a pinned baseline manifest on each saved schedule draft successor with hard and soft dependency version ids.
3. On save, rematerialize fresh matching companion evidence for the new draft version, including a machine-readable calculation snapshot.
4. Make artifact-backed schedule contract resolution use the selected draft version and its pinned companions rather than latest run artifacts.
5. Add hard dependency-drift guards so route-demand / availability / capability / actual-hours changes block submit or publish where appropriate.

## Verification
- new preview endpoint/action tests
- new tests proving saved draft versions get fresh calculation snapshot companions
- new tests proving artifact-backed views no longer show mismatched current-state calculations
- new tests proving drift blocks publish and surfaces dependency state correctly

## Acceptance criteria
- Unsaved schedule edits can be previewed without materializing a new artifact version.
- Saved draft successors produce pinned calculation evidence tied to that draft version.
- Artifact-backed schedule pages use the selected draft’s own baseline and companions.
- Hard dependency drift is explicit and fail-closed at submit/publish boundaries.
