# Logistics Workpages - Unified replan popup and dynamic scheduling activation plan

## Why this exists
EPIC-131 froze a clean operator boundary for Workpages v1:
- `schedule-v0` owns bounded reassignment/on-call edits plus server recalculation
- `route-demand-v0` owns route-demand truth
- `driver-preferences-v0` stays advisory
- day-of replan remained outside the weekly workpage boundary

That tranche deliberately deferred:
- date-specific driver exceptions
- automatic route-demand-triggered rescheduling
- a stronger operator-facing replan experience

The current repo now has enough weekly/live runtime truth, workpage seams, and deterministic schedule-control services to select the next bounded tranche:

`shared schedule popup surface -> weekly-backed proposal/build before publish -> live-dispatch-backed repair/replan after publish`

This plan freezes that architecture before implementation begins.

## Repo-grounded current state

### 1. The app shell already owns the shared chrome and quick-edit modal affordances
`frontend/src/app/AppShell.tsx` already:
- renders the top-left identity chip
- owns `Drivers`, `Edit weekly schedule`, `Edit route demand`, and `Menu`
- opens embedded quick-edit modals for drivers, schedule, and route demand

The next tranche should reuse that shell posture instead of adding a second operator surface.

### 2. The schedule popup is still weekly-draft-centric today
`frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx` currently owns:
- schedule preview recalculation
- schedule draft save
- direct Sick / No Show mutation
- artifact-version refresh and reopen behavior

`frontend/src/components/workpages/ScheduleWorkpageSurface.tsx` renders the heatmap and status/pill surfaces, but it does not yet understand:
- proposal review
- ranked replacement candidates
- canonical execution status
- lifecycle-split ownership

### 3. The current Sick / No Show path is a weekly draft successor flow
`src/onetruth/application/handlers/workpage_schedule_commands.py` currently:
- creates a canonical approved availability exception
- pins the resulting approved-availability artifact back into the weekly draft dependency manifest
- clears the selected assignment/reserve rows
- creates a new superseding weekly schedule draft

That is a truthful bounded weekly-draft implementation for the current popup, but it is not the right long-term owner for post-publish day-of control.

### 4. Route-demand saves still create drift/refresh follow-up, not proposal/replan work
`route-demand-v0` currently:
- saves immutable successors for `planning.route_slot_requirements.workbook`
- keeps schedule artifacts pinned to their own baseline
- creates or reopens schedule refresh follow-up truth when demand drifts from the current schedule draft baseline

That is still correct for the current v1 boundary, but it is not yet the selected greenfield scheduling trigger model.

### 5. The only mature scheduler agent runtime today is the weekly Stage04 human-task path
`src/onetruth/application/services/weekly_stage04_openai_agent.py` and the current API surface provide a bounded runtime only for:
- a claimed Stage04 `work_item` human task
- backed by canonical `task_run`, `execution_session`, `tool_execution`, and policy evidence

This runtime is not a generic “run scheduler” button. EPIC-135 must reuse that truth before publish rather than bypassing it.

### 6. Stage04 input truth is explicit and cannot be silently removed
`src/onetruth/application/services/schedule_control/stage04_input_registry.py` and
`src/onetruth/application/services/task_requirements.py` show that the weekly scheduler depends on canonical input bindings, especially:
- `planning.route_slot_requirements.workbook`
- `planning.driver_capabilities.workbook`
- operationally also `planning.approved_availability.workbook`
- operationally also `planning.actual_hours_snapshot.workbook`

Removing the visible scheduler task from the operator to-do flow does not remove those prerequisites.

### 7. Live dispatch is the correct owner after publish, but it requires the weekly handoff
`docs/workflows/live_dispatch/v1/OPERATING_MODEL.md` and
`src/onetruth/application/handlers/logistics_handoff.py` show that live dispatch is anchored on:
- immutable published weekly seed truth
- service-date activation
- issue/delta promotion over the base seed

That means a pure live-dispatch design cannot own pre-publish behavior because there is no published `dispatch.base_schedule_seed.workbook` yet.

### 8. Deterministic candidate logic already exists and should be reused first
The current schedule-control stack already has:
- hard-filter candidate generation
- deterministic scoring
- schedule checks and driver metrics

So the next tranche should default to:
- deterministic ranking first
- agent auto-run only for selected greenfield activation
- agent escalation second for harder brownfield repair

### 9. There is no canonical driver-contact authority yet
The current weekly examples, workpage projections, and scheduling artifacts do not carry driver phone numbers.

EPIC-135 must add a new read-side contact authority rather than storing contact data inside driver capabilities or local demo-only UI state.

## Architecture frozen for EPIC-135

### 1. One shared popup surface, two backend ownership lanes
The operator-facing control surface remains the shared `Edit Weekly Schedule` popup.

Ownership is split by lifecycle state:
- before publish: `weekly_schedule_planning.v1`
- after publish: `live_dispatch.v1`

UI reuse does not change workflow ownership.

### 2. Pre-publish lane: weekly-backed proposal/build flow
Before weekly publish truth exists:
- the popup remains a weekly-backed surface
- `0 -> N` route additions inside the active weekly scope auto-trigger scheduling
- the trigger must create or reuse canonical weekly task/execution context
- the existing weekly Stage04 agent runtime remains the agent path
- brownfield pre-publish changes use deterministic proposal generation first

### 3. Post-publish lane: live-dispatch-backed repair and replan
After weekly publish truth exists:
- sick/no-show and route-demand increases move into issue-scoped live-dispatch replan work
- the base weekly seed stays immutable
- the popup becomes a projection over live-dispatch draft/issue state
- proposal apply/ignore flows operate on live-dispatch replan truth, not direct weekly-draft mutation

### 4. Greenfield vs brownfield
Use one shared repair vocabulary:
- `greenfield_initial_fill`: a day crosses `0 -> N` routes
- `brownfield_repair`: existing staffed day changes, including sick/no-show and incremental route change

Trigger rules:
- greenfield inside active scope auto-runs the scheduler agent
- brownfield uses deterministic proposal first
- brownfield escalates to an agent only when deterministic repair is not enough or the user explicitly requests it

### 5. Two-week route-demand truth stays valid
The current two-week route-demand horizon remains canonical route-demand truth.

Auto-scheduling only fires when:
- the changed service date is inside the active weekly planning scope before publish, or
- the changed service date is inside an activated live-dispatch day after publish

Out-of-scope future dates still save as route-demand truth, but they do not auto-open replanning.

### 6. Canonical agent-working status is runtime truth, not UI inference
The popup’s progress/status surface must be backed by canonical runtime objects:
- `task_run`
- `human_task`
- `execution_session`
- `tool_execution`

The popup must not derive “agent is working” from local mutation state, timers, or optimistic heuristics.

### 7. Separate contact authority
Add one new canonical contact artifact family:
- `planning.driver_contact_directory.workbook`

This artifact:
- stays separate from driver capabilities
- is read-side only in this epic
- is joined into weekly/live replan projections so the popup can show phone numbers for top picks and all other eligible drivers

## Public interface changes to freeze early

### Shared workpage contract additions
The schedule popup contract must grow additive server-authored blocks for:
- `replan_context`
- `proposal_state`
- `proposal`
- `top_candidates`
- `other_candidates`
- `blocked_candidates`
- `execution_status`

Recommended shape:

```text
replan_context:
  lifecycle_phase: pre_publish | post_publish
  workflow_owner: weekly_schedule_planning.v1 | live_dispatch.v1
  issue_kind: route_added | route_increase | sick_no_show | manual_repair
  repair_mode: greenfield_initial_fill | brownfield_repair
  trigger_origin: route_demand_save | schedule_cell_action | manual_replan
  service_date: YYYY-MM-DD | null
  active_scope_start: YYYY-MM-DD | null
  active_scope_end_exclusive: YYYY-MM-DD | null

proposal_state:
  pending | ready | applied | ignored | blocked | failed

execution_status:
  task_run_id
  human_task_id
  execution_session_id
  current_state
  phase_label
  started_at
  updated_at
  blocking_reason_code | null
  failure_reason | null
```

### Candidate metrics
Each candidate row must carry:
- driver identity
- phone number
- on-call posture
- availability state
- preference state
- rolling-7 projected hours
- remaining headroom
- hard-filter reasons
- projected checks / coverage impact

Grouping rules:
- `top_candidates` = top 3 hard-pass candidates
- `other_candidates` = remaining hard-pass candidates
- `blocked_candidates` = excluded candidates with explicit reasons

On-call priority applies only after hard-filter pass.

### Compatibility rule
Current direct actions such as `workpage.schedule-v0.mark_sick_no_show` may remain temporarily as fallback compatibility affordances, but the primary operator path moves to the shared replan/proposal contract.

## Implementation order

### TASK-0225
Freeze the unified replan boundary, lifecycle split, prerequisite truth, and repo memory.

### TASK-0226
Add shared replan contract blocks and canonical runtime-status projection.

### TASK-0227
Add driver-contact authority and deterministic candidate/compliance projection.

### TASK-0228
Implement the pre-publish weekly-backed replan adapter and in-scope `0 -> N` route-demand trigger.

### TASK-0229
Implement the post-publish live-dispatch replan adapter over base-seed plus delta truth.

### TASK-0230
Add the live-dispatch agent runtime for greenfield auto-run and bounded brownfield escalation.

### TASK-0231
Redesign `Edit Weekly Schedule` into the shared proposal-review and manual-override popup.

### TASK-0232
Remove the operator-facing manual scheduler UX, update demo truth, and close the epic with regressions and repo-memory sync.

## Verification themes
- contract tests for proposal, candidate, contact, and execution-status blocks
- weekly pre-publish tests for Stage04 prerequisite blocking and in-scope `0 -> N` activation
- live-dispatch tests for post-publish sick/no-show and route-increase issue-scoped replan truth
- frontend popup tests for greenfield/brownfield shared rendering, stacked-modal launch, and canonical status surfaces
- canonical demo verification for greenfield activation, brownfield absence replacement, phone-number display, and agent-working visibility

## Stop line
- Do not store phone numbers in driver capabilities.
- Do not keep proposal state only in React.
- Do not treat weekly-draft mutation as the long-term owner of post-publish day-of repair.
- Do not add popup-only spinner/timer status.
- Do not silently remove Stage04 required-input gates just because the manual task CTA is going away.
- Do not let route-demand saves auto-trigger replanning outside the active weekly/live scope.
