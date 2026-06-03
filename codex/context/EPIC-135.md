# EPIC-135 Context Pack - Unified schedule replan popup and dynamic scheduling activation

Purpose:
- Rehydrate the selected next app-facing workpage epic after EPIC-134.
- Keep the implementation grounded in the existing weekly/live authority model instead of widening the weekly popup ad hoc.

## Current landed subset (2026-05-10)
- A bounded pre-publish weekly-draft route-demand coverage slice is now implemented.
- Existing-week positive route-count increases can hand off from `route-demand-v0` into the shared `schedule-v0` quick-edit popup with backend recommend/apply coverage actions.
- Future-week `Save and run scheduling agent` remains the separate weekly Stage04 greenfield activation path.
- This does not imply that the later live-dispatch-backed replan lane, canonical runtime-status projection, driver-contact bridge, or manual scheduler CTA retirement are complete.

## Non-negotiable invariants
- One truth system: workpages remain projections over canonical workflow/task/event/artifact/pointer truth.
- `weekly_schedule_planning.v1` owns pre-publish schedule build/review truth.
- `live_dispatch.v1` owns post-publish sick/no-show and day-of route-change resolution truth.
- One shared popup surface must not collapse those ownership boundaries.
- Scheduler “working” status must come from canonical runtime objects plus existing requirement/actionability truth, not popup-local inference.
- Phone numbers must live in mirrored weekly/live contact bridge inputs, not in driver capabilities.
- The published weekly base schedule remains immutable after handoff.
- The old route-demand refresh-task spawn path must be replaced before the manual scheduler CTA is retired.

## Authoritative docs
- `docs/planning/epics/EPIC-135.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_UNIFIED_REPLAN_AND_DYNAMIC_SCHEDULING_PLAN.md`
- `codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Repo-grounded findings
1. `AppShell` already owns the top-chrome quick-edit modal posture for schedule, route demand, and drivers.
2. The current schedule popup is weekly-draft-centric and currently owns direct Sick / No Show mutation.
3. Existing-week positive route-count increases now hand off into pre-publish weekly-draft coverage recommendations, while the later live-dispatch-backed replan/runtime-status/contact-data/manual-CTA work remains open.
4. The weekly Stage04 human-task endpoint is the only mature scheduler agent runtime today and it requires a claimed Stage04 `work_item`.
5. Stage04 required-input truth plus requirement/actionability truth are explicit and cannot be bypassed when the manual scheduler CTA is removed.
6. Live dispatch requires published weekly seed truth and therefore cannot own the pre-publish lane.
7. Deterministic candidate generation/scoring/validation already exists and should be reused first.
8. There is no canonical driver-contact authority yet, and a planning-only contact dataset would be insufficient for the post-publish lane.
9. There is no authored live-dispatch agent/runtime surface yet; popup work should not wait on it.

## Preferred implementation shape
- freeze the shared popup contract and lifecycle split first
- add canonical runtime-status and candidate/contact projection before redesigning the popup UI
- reuse the existing weekly agent runtime before publish and replace the current refresh-task creation path during that work
- ship the shared popup over weekly/live deterministic truth before the later live-dispatch agent/runtime task
- add the live-dispatch agent/runtime as a later explicit task instead of pretending it already exists
- keep demo truth canonical and route-scoped; do not add a second demo mode

## Stop line
- no browser-side ranking
- no popup-only spinner/timer progress
- no long-term weekly-draft mutation path for post-publish repair
- no phone numbers in driver capabilities
- no planning-only contact dataset for a weekly/live popup surface
- no silent removal of Stage04 prerequisite gates
