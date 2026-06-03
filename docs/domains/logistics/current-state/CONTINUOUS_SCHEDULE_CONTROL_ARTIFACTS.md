> Document classification: normative logistics current-state source. See `docs/domains/logistics/DOC_INVENTORY.yaml`.

# CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md

## Purpose
Lock the authored artifact semantics for the first serious schedule-control logistics slice (`weekly_schedule_planning.v1` Stage04 and `live_dispatch.v1` Stage02) without introducing a second truth path.

## Classification Matrix
| Class | Artifact key(s) | Authority posture |
|---|---|---|
| Canonical | `planning.route_slot_requirements.workbook`, `planning.driver_capabilities.workbook`, `planning.driver_shift_preferences.workbook`, `planning.input_bundle.doc`, `planning.candidate_schedule_delta.workbook`, `dispatch.route_slot_requirements.workbook`, `dispatch.driver_capabilities.workbook`, `dispatch.input_bundle.doc`, `dispatch.candidate_schedule_delta.workbook` | Immutable artifact versions linked to canonical workflow/task/event lineage. `planning.driver_shift_preferences.workbook` remains advisory input, but it is still canonical artifact truth for that advisory surface. |
| Draft-review | `planning.draft_weekly_schedule.workbook` | Immutable Stage04 draft artifact versions in the canonical run chain. These are the bounded `schedule-v0` edit surface, but they are not official weekly truth until Stage06 publication/pointer promotion. |
| Derived | current operative schedule view (materialized from published weekly base + daily seed + ordered promoted live deltas), open-exceptions packet (materialized from canonical flags) | Convenience/projection outputs only; never authoritative by themselves. |
| Evidence | `planning.validation_summary.doc`, `planning.draft_weekly_schedule.doc`, `planning.schedule_calculation_snapshot.json`, `planning.manager_review.doc`, `planning.publish_packet.doc`, `dispatch.validation_summary.doc`, `dispatch.issue_board.doc`, `dispatch.change_notice.doc` | Human/operator review evidence and machine-readable calculation evidence; does not define official schedule truth. |
| Prohibited | authoritative `planning.current_schedule_plan*`, authoritative `planning.open_exceptions*`, authoritative `dispatch.current_schedule_plan*`, authoritative `dispatch.open_exceptions*`, any peer `agent_runs` truth subsystem | Must not be introduced as canonical state authority. |

## Stage Bindings
- `weekly_schedule_planning.v1` `Stage04` consumes canonical bundle + bridge inputs and emits machine-checkable candidate + validation artifacts plus the immutable `planning.draft_weekly_schedule.workbook` draft-review artifact for Stage05 review.
- `weekly_schedule_planning.v1` `Stage04` may also carry optional advisory `planning.driver_shift_preferences.workbook` input when a snapshot exists; absence remains allowed.
- `weekly_schedule_planning.v1` `Stage05` records manager review evidence against that Stage04 draft artifact and may route changes back to Stage04 or forward toward Stage06 publication.
- `live_dispatch.v1` `Stage01` binds service-day bridge inputs (`route_slot_requirements`, `driver_capabilities`) alongside base seed and intake events.
- `live_dispatch.v1` `Stage02` consumes canonical bundle + bridge inputs and emits machine-checkable candidate + validation artifacts for dispatcher/approval flow.

## Authority Invariants
- Official weekly truth is still only the promoted `planning.published_weekly_schedule.workbook` pointer outcome (`Stage06`).
- `planning.draft_weekly_schedule.workbook` is a canonical draft-review artifact in the weekly run chain, but it is not official published schedule truth.
- `planning.route_slot_requirements.workbook` is edited through `route-demand-v0`, not through `schedule-v0`.
- `planning.driver_shift_preferences.workbook` is edited through `driver-preferences-v0` and stays advisory only.
- Official live truth is still only ordered promotion of `dispatch.official_replan_delta.workbook` (`Stage05`).
- Current schedule materialization remains derived from canonical base + seed + ordered deltas.
- Open exceptions remain sourced from canonical `flags` state and timeline events.
