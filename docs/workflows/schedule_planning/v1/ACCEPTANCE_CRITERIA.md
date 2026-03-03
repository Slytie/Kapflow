# ACCEPTANCE_CRITERIA.md - Schedule Planning v1

These criteria are intended to become the executable spec for the Schedule Planning workflow pack.

## Happy path (minimum)
- [ ] Given `ScheduleDateID` `SD-YYYY-MM-DD` and scope `(tenant_id, domain_id)`, when official inputs are promoted, then a schedule planning workflow run can progress Stage03->Stage07 to completion.
- [ ] `workflow.run.created` records the service interval, logical date, and service timezone for the run.
- [ ] Timeline contains a complete sequence of events with strong links: `workflow_run_id`, `task_run_id`, `human_task_id`, `approval_id`, `artifact_version_id`, and pointer promotions.
- [ ] If a completed task causes re-review, information gathering, or final review, the child task run is emitted explicitly rather than hidden in mutable task state.
- [ ] Stage06 publishes a stable base schedule as an official promoted artifact.
- [ ] Stage07 records at least one explicit replan delta without mutating the original published schedule version.

## Fully-agentive debug slice (Stage 4 priority)
- [ ] In a designated debug tenant, each in-scope stage Stage03->Stage07 can be exercised through agent-owned work so the whole orchestration path is debug-visible end-to-end.
- [ ] `execution.session.*` and `tool.execution.*` events show the lineage of agent-owned work without becoming a second state system.
- [ ] Stage06 and threshold-triggered Stage07 approvals still emit `approval.requested` and `approval.responded`; the fully-agentive slice must not bypass the canonical approval object model.
- [ ] Official state changes still occur only through canonical events, immutable artifact versions, and pointer promotions.
- [ ] No agent-only transcript, cache, or side channel may become authoritative workflow state.

## Core negative cases (must pass)
### AC-1 Loose promotion records exact version
- [ ] Approve & Promote Latest promotes the current latest eligible artifact version.
- [ ] Timeline records `promoted_artifact_version_id`.

### AC-2 Drift after review is visible
- [ ] If a newer version exists at time-of-promotion than the version reviewed, then emit `artifact.pointer.drift_detected` and surface it in timeline/UI.

### AC-3 Publish vs replan remains auditable
- [ ] If a no-show / call-out / vehicle issue occurs after publication, then the system creates a new artifact version or replan delta rather than mutating the published schedule in place.
- [ ] Timeline links the replan delta to the superseded published assignment(s).

### AC-4 Major replan requires approval
- [ ] If an intraday replan exceeds a documented threshold (overtime, contractor activation, SLA waiver, or zone-level capacity override), then approval is requested and recorded before the replan becomes official.
- [ ] Approval metadata captures who/when/method/notes.

### AC-5 Fail-open exporters (degraded audit visibility)
- [ ] If export/index is down, then state transitions still succeed AND authoritative timeline events still exist.
- [ ] Degraded mode is visible and alertable.

### AC-6 Domain partition enforcement
- [ ] Cross-tenant and cross-domain reads/writes are denied and logged.
- [ ] Background consumers enforce the same rules (exports, indexers, workers).
- [ ] If a cross-scope attempt occurs inside an execution session, the denial is visible through canonical execution / policy evidence.

### AC-7 Lease expiry and wakeup recovery
- [ ] If issue-specific work is claimed and then stalls, `task.lease_expired` reopens or escalates the work with visible evidence.
- [ ] A reconciler can recover a dropped wakeup without duplicating the Stage07 issue task.

## Schedule-planning-specific constraints
- [ ] Availability artifacts store only coded absence/leave types; no medical or disciplinary detail.
- [ ] Published schedule pins worker/zone/time-window assignments, break placeholders, and service interval semantics.
- [ ] Exception board records reason codes for at least: `no_show`, `vehicle_issue`, `delay_cluster`, `address_issue`, `weather_disruption`.
- [ ] Each Stage07 issue task is deduped by an activation key equivalent to `(workflow_run_id, flag_id, task_kind, generation)`.
- [ ] Retrying the same parent completion does not duplicate spawned child tasks.

## Overlay consistency
- [ ] Decision catalog references only valid stage IDs and actions for this workflow.
- [ ] Execution profile references only valid stage IDs, tool classes, and required evidence keys for this workflow.
- [ ] Event inventory references only valid event types in the canonical registry.
- [ ] Any generated runbook or CompanyOS IR derived from this pack does not invent official outputs or approvals outside the canonical files.
