# EPIC-135 Context Pack - Unified schedule replan popup and dynamic scheduling activation

Purpose:
- Rehydrate the selected next app-facing workpage epic after EPIC-134.
- Keep the implementation grounded in the existing weekly/live authority model instead of widening the weekly popup ad hoc.

## Non-negotiable invariants
- One truth system: workpages remain projections over canonical workflow/task/event/artifact/pointer truth.
- `weekly_schedule_planning.v1` owns pre-publish schedule build/review truth.
- `live_dispatch.v1` owns post-publish sick/no-show and day-of route-change resolution truth.
- One shared popup surface must not collapse those ownership boundaries.
- Scheduler “working” status must come from canonical runtime objects, not popup-local inference.
- Phone numbers must live in a separate contact authority, not in driver capabilities.
- The published weekly base schedule remains immutable after handoff.

## Authoritative docs
- `docs/planning/epics/EPIC-135.md`
- `docs/planning/LOGISTICS_WORKPAGES_UNIFIED_REPLAN_AND_DYNAMIC_SCHEDULING_PLAN.md`
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
3. Route-demand saves still create schedule refresh follow-up truth rather than proposal/replan truth.
4. The weekly Stage04 human-task endpoint is the only mature scheduler agent runtime today.
5. Stage04 required-input truth is explicit and cannot be bypassed when the manual scheduler task CTA is removed.
6. Live dispatch requires published weekly seed truth and therefore cannot own the pre-publish lane.
7. Deterministic candidate generation/scoring/validation already exists and should be reused first.
8. There is no canonical driver-contact authority yet.

## Preferred implementation shape
- freeze the shared popup contract and lifecycle split first
- add canonical runtime-status and candidate/contact projection before redesigning the popup UI
- reuse the existing weekly agent runtime before publish
- add the live-dispatch agent/runtime as a later explicit task instead of pretending it already exists
- keep demo truth canonical and route-scoped; do not add a second demo mode

## Stop line
- no browser-side ranking
- no popup-only spinner/timer progress
- no long-term weekly-draft mutation path for post-publish repair
- no phone numbers in driver capabilities
- no silent removal of Stage04 prerequisite gates
