> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md

## Purpose
This plan supersedes the earlier operator-workpages packet where several SME requests were interpreted too broadly.

The corrected product model is:

```text
W_schedule = Projection(schedule_artifact_under_view, hard_dependencies, soft_dependencies, calculation(schedule_artifact, dependencies, in_page_edits))
```

where:
- \(A_{schedule}\) is the weekly schedule artifact under view,
- \(I_{hard}\) are hard dependencies such as route demand, approved availability, driver capabilities, and actual-hours truth,
- \(I_{soft}\) are advisory dependencies such as driver preferences,
- \(\Delta\) are bounded in-page schedule edits,
- \(C\) is a deterministic calculation and compliance function used for preview and save.

A separate operational route-demand surface remains valid:

```text
W_route_demand = Projection(route_demand_artifact, demand_calculation(route_demand_artifact))
```

The key correction is that **schedule heatmap edits and route-demand edits are different operations over different truth objects**.

## SME clarifications now frozen
1. The request is **not about EOD**. Route changes can happen at any time.
2. The schedule-workpage change is primarily about **moving routes between drivers** using the existing heatmap paradigm, not about changing route counts per day inside the schedule editor.
3. Top arrows should navigate **accepted versions only**.
4. Driver preferences are **soft/advisory**, but high priority.
5. Route-demand changes should create **drift / rerun follow-up**, not automatic agentic re-scheduling, in v1.
6. Date-specific schedule exceptions remain out of scope for this packet.

## Grounded repo findings that matter

### 1. The current schedule editor already matches the "move routes between drivers" boundary
In `src/onetruth/application/services/schedule_control/draft_workbook.py`:
- `EDITABLE_SCHEDULE_DRAFT_FIELDS = {"assigned_driver_id", "assignment_status"}`
- row identity is fixed by `(service_date, route_slot_id)`
- immutable fields cannot change on submit

This means the schedule editor is already architecturally aligned with **reassignment / on-call changes** rather than route-demand editing.

In `frontend/src/components/workpages/ScheduleHeatmapEditor.tsx`:
- the current heatmap arms a filled cell and moves or swaps work on the **same service date**,
- which is consistent with reassigning routes between drivers.

So the near-term schedule work is **not** to invent a new edit model. It is to add live recalculation, compliance feedback, and richer metrics around the existing bounded edit model.

### 2. The current schedule save path is incomplete for calculated editing
In `src/onetruth/application/handlers/workpages.py`:
- `submit_schedule_artifact_workpage_command(...)` creates a new `planning.draft_weekly_schedule.workbook` version,
- but it does not rematerialize a fresh machine-readable calculation snapshot,
- and current workpage contract resolution does not reliably pin companion evidence to the selected draft version.

This is insufficient once the page displays top-bar totals, driver-level metrics, compliance checks, available-driver counts, and capacity posture.

### 3. Artifact-backed schedule views are still rebuilt against latest run inputs
In `src/onetruth/application/services/logistics_workpages.py`:
- `build_schedule_artifact_workpage_contract(...)` rebuilds schedule context from the run,
- and today it can mix an older schedule draft workbook with newer upstream inputs.

That is unacceptable once route-demand changes, preferences change, or accepted/draft navigation becomes important.

### 4. The repo already has the right calculation primitives
The weekly schedule stack already contains reusable building blocks:
- `schedule_control/bundle_builder.py`
- `schedule_control/validation.py`
- `schedule_control/route_slot_requirements.py`
- schedule heatmap payload builders in `logistics_workpages.py`

So the correct architecture is not a second truth system. It is a **preview/save calculation layer** over the existing schedule-control bundle and validation primitives.

### 5. "Dispatch workpage" should not be implemented by stretching `eod-v0`
The current `eod-v0` is the dispatch-reporting workflow surface, not an operational route-demand editor.

For the SME request about plus/minus route changes per day, the correct interpretation remains:
- keep `schedule-v0` for driver assignment edits,
- add `route-demand-v0` for demand adjustments,
- let schedule surfaces consume route demand as a dependency.

## Architecture now frozen for this packet

### 1. Workpages remain distinct from artifacts
Artifacts and workpages are not one-to-one.

The current weekly operator slice now has at least these truth objects:
- `planning.draft_weekly_schedule.workbook`
- `planning.published_weekly_schedule.workbook`
- `planning.route_slot_requirements.workbook`
- `planning.driver_shift_preferences.*` (new)
- supporting availability / capabilities / actual-hours artifacts

And these workpages:
- `schedule-v0`
- `route-demand-v0`
- `driver-preferences-v0`

### 2. The schedule page is a calculated workpage
The schedule page must expose server-authored blocks for:
- `calculations.top_bar`
- `calculations.driver_metrics`
- `calculations.checks`
- `calculations.selected_day`
- `dependencies[]`
- `draft_lineage`
- `accepted_series`
- `artifact_state`
- `actions[]`

### 3. Preview and save use the same deterministic calculation core
For unsaved edits:

```text
Preview(schedule_draft + in_page_edits, hard_dependencies, soft_dependencies) -> preview_calculations
```

For save:

```text
Save(schedule_draft + in_page_edits, pinned_baseline) -> new_schedule_draft + companion_evidence
```

where `E^{k+1}` includes companion evidence for the saved draft.

### 4. Add a machine-readable schedule calculation snapshot companion
Every saved schedule draft successor should rematerialize a machine-readable derived artifact, for example:
- `planning.schedule_calculation_snapshot.json`

This companion is **derived evidence**, not business truth.
It lets artifact-backed views, accepted-version views, and side-rail navigation render pinned metrics and checks without silently recomputing against newer upstream inputs.

### 5. Route-demand edits remain separate from heatmap edits
The schedule heatmap reassigns work between drivers and on-call positions.
It does **not** directly change route demand.

A separate `route-demand-v0` workpage edits route-demand truth using plus/minus interactions and day summaries.
Its saves create immutable successors and may trigger schedule dependency drift.

### 6. Accepted series is separate from draft lineage
- `draft_lineage`: supersedes chain of draft versions
- `accepted_series`: ordered official weekly schedule artifacts across prior/next weeks

Top arrows navigate **accepted series only**.
Draft lineage remains a separate side rail.

### 7. Preferences are soft inputs
`driver-preferences-v0` captures day-of-week preferences:
- definitely_can_not_work
- open_to_work
- prefer_not_to_work

These feed availability cues and optional highlighting, but do not block scheduling truth in this tranche.

## Additional defaults and grey areas

### Accepted series grouping (default)
Interpret “previous / next accepted versions” as:
- official weekly schedules for the **same operation / site / team / planning scope**,
- ordered by operational week.

Current repo review did **not** find a stable explicit artifact-level scope key for that grouping on saved/published schedule artifacts.
If the repo does not already expose a stable explicit scope key for that grouping, add one in this epic rather than inferring forever from ad hoc metadata.

### Route-demand +/- semantics (default)
The UI request is day-oriented, while `planning.route_slot_requirements.workbook` is slot-oriented.

Default implementation rule:
- the backend remains authoritative for mapping day-level plus/minus intent onto the underlying route-demand rows,
- the frontend must not invent slot-allocation heuristics,
- if the current artifact shape lacks a stable editable daily bucket, add a small route-demand normalization helper instead of pushing the ambiguity into the UI.

Current repo review found backend-owned daily buckets via `daily_demand_rows`, so this remains a fallback rule rather than the default first move.

### Accepted arrows on draft pages (default)
The arrows always traverse accepted series only.
The draft page may still display the accepted-series rail and arrow controls, but draft traversal remains separate and never shares the same controls.

## Implementation order
1. Freeze the clarified SME decisions and the corrected boundary between schedule edits and route-demand edits.
2. Land backend workpage-descriptor and contract changes for calculations, dependencies, accepted series, draft lineage, and action execution.
3. Land schedule preview/recalculation, pinned baseline manifests, companion calculation snapshot artifacts, and drift guards.
4. Land schedule frontend overhaul for live recalculation, top bar, driver metrics, checks, available-driver cues, and accepted/draft rails.
5. Land `route-demand-v0` for operational plus/minus edits and schedule drift propagation.
6. Land `driver-preferences-v0` and soft advisory integration.
7. Close tests, docs, compatibility cleanup, and deferred-item markers.

## Stop line
- Do not implement the schedule request by changing route demand inside `schedule-v0`.
- Do not treat `eod-v0` as the operational route-demand editor.
- Do not show derived schedule metrics from stale or mismatched companions.
- Do not silently recompute artifact-backed schedule views against newer hard dependencies.
- Do not conflate accepted-series navigation with draft traversal.
