# Schedule Planning v1 - operating model (same-day delivery, ~200 employees)

## Why this workflow exists
A same-day delivery operator cannot rely on a single static schedule artifact. The workflow must:
1. publish a stable base plan early enough for drivers, supervisors, and hubs to execute confidently;
2. respect tight delivery time windows, start/end windows, and break constraints;
3. absorb inevitable disruptions such as no-shows, vehicle issues, delay clusters, and demand spikes;
4. preserve an audit trail showing what changed, why, and who approved it.

This workflow therefore separates:
- base publication (Stage06)
- live-day exception control / replan (Stage07)

## Temporal partition contract
Schedule Planning is a service-day workflow, not just a date bucket.

For each `ScheduleDateID`, the authoritative runtime must be able to pin:
- `service_timezone`
- `service_interval_start`
- `service_interval_end`
- `logical_date = service_interval_start`
- interval closure rule `[start,end)`

This distinction matters because there are always two times in play:
- the time the schedule is **about** (the service interval)
- the time the platform **executes** work (planning, publication, or replan time)

### Policy defaults for Stage 4
- default service timezone: `Europe/Berlin` unless the config workbook says otherwise
- catchup policy: `manual_only`
- historical backfill policy: `explicit_operator_request`
- stage rerun policy: create a new `task_run` inside the same `workflow_run`

## Problem decomposition

### 1) Coverage and staffing plan
At a high level, the service-date staffing plan can be modeled as:

\[
\min \; J =
lpha \sum_{z,h} u_{z,h}
+ eta \sum_i o_i
+ \gamma \sum_i c_i
+ \delta \sum_r q_r
\]

where:
- \(u_{z,h}\) = uncovered courier-hours in zone \(z\), time bucket \(h\)
- \(o_i\) = overtime assigned to worker \(i\)
- \(c_i\) = schedule-change cost against the previously communicated plan
- \(q_r\) = expensive recovery actions (contractor activation, SLA waiver, cross-zone override)

subject to:
- worker availability and shift-length limits
- qualification / vehicle-class requirements
- break placement requirements
- minimum zone-hour coverage from the demand forecast
- hub / vehicle availability limits

This produces the capacity plan (Stage04).

### 2) Draft schedule and route-bundle feasibility
The next layer assigns people, vehicles, and bundles to feasible windows. Conceptually this is a vehicle-routing / pickup-delivery problem with time windows and resource constraints:
- delivery windows
- vehicle start/end windows
- break rules
- service-time assumptions
- zone / hub compatibility

The output is a draft schedule plus a triage list of constraint violations and operational risks (Stage05).

### 3) Intraday replan
Once Stage06 publishes the schedule, the optimization target changes. Intraday control should minimize service risk *and* change cost:

\[
\min \; J_{live} =
\lambda_1 \cdot 	ext{missed_window_risk}
+ \lambda_2 \cdot 	ext{unassigned_priority_stops}
+ \lambda_3 \cdot 	ext{replan_churn}
+ \lambda_4 \cdot 	ext{overtime/outsourcing}
\]

The critical product rule is:
- never silently edit the published schedule
- issue a new version / delta artifact with strong links to what it supersedes

## Eligibility and activation model
Schedule Planning should not be treated as one giant linear DAG run. Eligibility is stage-scoped.

For a stage \(j\):

\[
Eligible_j(r,t) = Deps_j(r) \land Inputs_j(r) \land Gates_j(r,t) \land 
eg Stale_j(r)
\]

Where:
- `Deps_j` means predecessor stage or prior transition requirements are satisfied
- `Inputs_j` means the required official inputs for the interval are pinned
- `Gates_j` means approvals, timers, or threshold rules are satisfied
- `Stale_j` means a required pointer moved after the stage snapshot was pinned

### Stage07 activation rule
Stage07 is issue-scoped, not a free-running loop. Each issue-specific activation should carry an activation key equivalent to:

`(workflow_run_id, flag_id, task_kind, generation)`

That prevents duplicate issue work under retries or repeated wakeups.

## Roles and review model

### Core roles
- `schedule_planner` - prepares demand/capacity/draft artifacts
- `dispatch_supervisor` - reviews the draft, resolves ordinary conflicts, publishes the base schedule
- `operations_manager` - approves major replans or policy/cost exceptions
- `fleet_coordinator` - resolves vehicle-specific constraints and outages
- `system_worker` - background orchestration / eventing actor

### Debug-tenant role posture
In designated debug tenants, the same roles may be held by designated agent principals. This allows end-to-end testing without introducing a second runtime model.

### Pre-publish review (Stage06)
The dispatch supervisor should explicitly review:
- uncovered zone-hours
- overtime concentration
- skill / license gaps
- break-placement risk
- priority-account / promised-window risk
- fairness or instability versus the prior communicated plan

### Live-day review (Stage07)
The operations manager should review:
- no-show / call-out that invalidates route coverage
- vehicle loss that removes capacity from a zone
- demand spikes that threaten priority windows
- ETA slippage or failed-task clusters that imply route-level recovery is no longer enough
- any replan requiring overtime beyond threshold, contractor activation, or SLA waiver

## Initial escalation defaults for MVP
These are design defaults, not claims about universal industry thresholds. Tune them with live data later.

Escalate to `dispatch_supervisor` when:
- any priority route bundle is uncovered at publish time
- a draft carries unresolved `undercoverage` or `skill_gap`
- more than 5% of assignments changed after the internal review cutoff

Escalate to `operations_manager` when:
- a zone has >10% uncovered courier-hours after all ordinary rebalancing
- any replan requires contractor activation or an SLA waiver
- average overtime added by replan exceeds 1 hour for the affected worker set
- one issue forces cross-zone override or hub-level capacity reprioritization

## Conditional follow-on task loops
Task completion may create explicit follow-on tasks.

Typical Stage05 / Stage06 examples:
- reviewer needs more information from `fleet_coordinator` or `schedule_planner`
- reviewer requests changes and sends the draft back for rework
- draft is otherwise complete and now requires a final review before publish

Typical Stage07 examples:
- the current issue creates a child issue that needs separate triage
- the replan cannot continue until missing operational information is gathered
- the major replan is complete and now needs final review

Rules:
- child tasks stay inside the same `workflow_run_id`
- child tasks must be explicit `task.run.created` / `task.created` evidence
- child tasks must be deduped by activation keys and bounded by spawn budgets
- retries of the same parent completion must not duplicate children

## Artifact principles
- Stage06 creates a stable base schedule.
- Stage07 creates replan deltas linked to the published schedule and to the triggering issue.
- Availability artifacts store coded leave/absence types only.
- Exception artifacts must carry reason codes, owners, and resolution status.

## Replay, rerun, and backfill
These concepts must remain distinct.

- **Retry**: same logical attempt, same idempotency key, no duplicate side effects.
- **Stage rerun**: a new `task_run` inside the same `workflow_run` after failure, staleness, or review.
- **Replay**: read-only reconstruction of workflow state from the authoritative event history.
- **Historical backfill**: explicit operator-requested creation of historical service-day runs, with separate concurrency controls.

Do not model recovery by clearing or mutating the existing published schedule state in place.
