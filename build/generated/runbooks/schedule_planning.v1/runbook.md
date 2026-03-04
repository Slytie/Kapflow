# Runbook Prototype - schedule_planning.v1

> Generated artifact (non-authoritative). Edit repo-native source files and regenerate.

## Workflow
- Workflow ID: `schedule_planning.v1`
- Workflow version: `v1`
- Name: Schedule Planning - Same-day delivery daily cycle

## Stage List and Purpose
- `Stage01` - Schedule_Config
- `Stage02` - Use coded leave/absence types only; do not store medical or disciplinary detail.
- `Stage03` - Demand is planned by service-date, zone, and time bucket.
- `Stage04` - Activation basis: Stage03_success
- `Stage05` - Draft schedule must preserve stability bias; changes against prior commitments need explicit reason codes.
- `Stage06` - Publishing creates the stable base schedule for the service day.
- `Stage07` - Major replan approval is required for contractor activation, overtime beyond threshold, SLA waiver, or zone-level capacity override.

## Artifact Keys by Stage
### Stage01
- `schedule.config.doc` (official_input)
- `schedule.config.workbook` (official_input)
### Stage02
- `schedule.worker_roster.doc` (official_input)
- `schedule.worker_roster.workbook` (official_input)
### Stage03
- `schedule.demand_forecast.doc` (evidence)
- `schedule.demand_forecast.workbook` (official_input)
### Stage04
- `schedule.capacity_plan.doc` (evidence)
- `schedule.capacity_plan.workbook` (official_input)
### Stage05
- `schedule.draft_schedule.doc` (evidence)
- `schedule.draft_schedule.workbook` (official_input)
### Stage06
- `schedule.supervisor_review.doc` (evidence)
- `schedule.published_schedule.workbook` (official_output)
### Stage07
- `schedule.exception_board.doc` (evidence)
- `schedule.replan_delta.workbook` (official_output)

## Decisions and Approvals
- `schedule.stage06.publish_base_schedule` (`Stage06`) -> action `publish_schedule`, requested_from `dispatch_supervisor`, responses: approve, reject, request_changes
- `schedule.stage07.approve_major_replan` (`Stage07`) -> action `approve_major_replan`, requested_from `operations_manager`, responses: approve, reject, request_changes

## Spawn Rules and Bounded Loops
- `Stage05`: policy `conditional_follow_on`, execution_pattern `linear_chain`, max_depth `2`
  - `stage05_request_operational_information` when `triage_requires_external_information` -> `Stage05` / `information_request` (roles: fleet_coordinator, schedule_planner)
  - `stage05_return_for_rework` when `triage_requires_schedule_revision` -> `Stage05` / `work_item` (roles: schedule_planner)
- `Stage06`: policy `conditional_follow_on`, execution_pattern `approval_gate`, max_depth `3`
  - `stage06_request_changes_to_draft` when `review_requests_changes` -> `Stage05` / `work_item` (roles: schedule_planner)
  - `stage06_request_missing_information` when `review_requires_more_information` -> `Stage06` / `information_request` (roles: fleet_coordinator, schedule_planner)
  - `stage06_final_publish_review` when `draft_is_publish_ready` -> `Stage06` / `final_review` (roles: dispatch_supervisor)
- `Stage07`: policy `issue_scoped`, execution_pattern `bounded_exception_loop`, max_depth `5`
  - `stage07_request_issue_information` when `replan_requires_missing_information` -> `Stage07` / `information_request` (roles: fleet_coordinator, schedule_planner)
  - `stage07_follow_on_exception_triage` when `resolution_creates_child_issue` -> `Stage07` / `exception_triage` (roles: operations_manager)
  - `stage07_final_replan_review` when `major_replan_is_ready_for_review` -> `Stage07` / `final_review` (roles: operations_manager)

## Operator Checklist Snippets (from ACCEPTANCE_CRITERIA)
- Given `ScheduleDateID` `SD-YYYY-MM-DD` and scope `(tenant_id, domain_id)`, when official inputs are promoted, then a schedule planning workflow run can progress Stage03->Stage07 to completion.
- `workflow.run.created` records the service interval, logical date, and service timezone for the run.
- Timeline contains a complete sequence of events with strong links: `workflow_run_id`, `task_run_id`, `human_task_id`, `approval_id`, `artifact_version_id`, and pointer promotions.
- If a completed task causes re-review, information gathering, or final review, the child task run is emitted explicitly rather than hidden in mutable task state.
- Stage06 publishes a stable base schedule as an official promoted artifact.
- Stage07 records at least one explicit replan delta without mutating the original published schedule version.
- In a designated debug tenant, each in-scope stage Stage03->Stage07 can be exercised through agent-owned work so the whole orchestration path is debug-visible end-to-end.
- `execution.session.*` and `tool.execution.*` events show the lineage of agent-owned work without becoming a second state system.
- Stage06 and threshold-triggered Stage07 approvals still emit `approval.requested` and `approval.responded`; the fully-agentive slice must not bypass the canonical approval object model.
- Official state changes still occur only through canonical events, immutable artifact versions, and pointer promotions.
- No agent-only transcript, cache, or side channel may become authoritative workflow state.
- Approve & Promote Latest promotes the current latest eligible artifact version.
- Timeline records `promoted_artifact_version_id`.
- If a newer version exists at time-of-promotion than the version reviewed, then emit `artifact.pointer.drift_detected` and surface it in timeline/UI.
- If a no-show / call-out / vehicle issue occurs after publication, then the system creates a new artifact version or replan delta rather than mutating the published schedule in place.
- Timeline links the replan delta to the superseded published assignment(s).
- If an intraday replan exceeds a documented threshold (overtime, contractor activation, SLA waiver, or zone-level capacity override), then approval is requested and recorded before the replan becomes official.
- Approval metadata captures who/when/method/notes.
- If export/index is down, then state transitions still succeed AND authoritative timeline events still exist.
- Degraded mode is visible and alertable.

## Source Inputs
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
