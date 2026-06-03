> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics Workpages - EPIC-125 Closeout and First-Demo Feedback Note

## Purpose
Record the repo-truth closeout for EPIC-125 and freeze the bounded first-demo feedback themes that later landed work consumed.

## Closeout status
- EPIC-125 is complete as of `2026-04-06`.
- `TASK-0154` is reconciled to `DONE` from existing runtime truth:
  - the live-dispatch completion path already produces `dispatch.official_replan_delta.workbook`
  - the weekly-first local demo smoke already walks the manual route-delta loop
  - the local and continuous operator runbooks already describe the live day-of replan lane
- `TASK-0157` closes the epic by aligning repo memory with that existing operator-loop truth and freezing the first-demo feedback handoff.

## First-demo feedback themes and downstream disposition
### 1. demo-shell and route discoverability needed simplification and canonical-route clarity
- EPIC-126 cleanup history removed stale demo-era wording and normalized active route posture.
- EPIC-133 made `/demo/logistics` launcher-only and pushed workpage/workspace validation onto canonical `/runs/:workflowRunId/*` surfaces.
- EPIC-134 added the deterministic prep command and canonical demo runbook so operators can validate canonical routes directly.

### 2. weekly schedule editing, route-demand truth, driver preferences, and live day-of control needed a clearer boundary split
- EPIC-126 cleanup history preserved the stop line that weekly schedule editing must not absorb live day-of control.
- EPIC-131 split the bounded workpage surfaces into `schedule-v0`, `route-demand-v0`, and `driver-preferences-v0` while keeping day-of change in `live_dispatch.v1`.
- EPIC-134 kept the canonical demo posture aligned to that boundary instead of introducing a second demo mode.

### 3. workpage lineage, latest-draft, and action semantics needed to move server-side
- EPIC-126 cleanup history kept canonical routes and active docs aligned while the workpage layer settled.
- EPIC-133 moved lineage/latest/accepted navigation and server-authored action execution behind backend-owned seams.
- The resulting canonical pages now render server-owned workpage truth instead of reconstructing workflow meaning client-side.

### 4. supported-environment and deterministic demo-prep truth needed to replace ad hoc local-demo assumptions
- EPIC-126 cleanup history established truthful closeout expectations around canonical-route proof and active-doc synchronization.
- EPIC-132 restored clean supported-environment verification lanes for the public workpage mutation boundary.
- EPIC-134 corrected the stale local-demo diagnosis, made reporting dependency failures honest, and added the deterministic canonical demo-prep path plus concise runbook.

## Still deferred for future selection
- date-specific driver exceptions
- automatic route-demand-triggered rescheduling
- broader feedback-driven operator hardening beyond the landed cleanup and demo-enablement tranches
- any live-dispatch algorithmic candidate-generation or widened day-of workpage scope
