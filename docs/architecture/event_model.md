# Event model

This repo has one event system.

## 1) One timeline
Business workflow progression, task runs, human tasks, approvals, execution sessions, tool execution, projection rendering, degraded-mode changes, and future method-governance events all emit through the same envelope and link model.

There is no separate "agent timeline" that outranks or bypasses the business timeline.

## 2) Actor taxonomy
Canonical actor types are:
- `human`
- `agent`
- `service`
- `system`

See `schemas/policy/governance_vocabulary.yaml`.

## 3) Event classes
The main event classes are:

### Run and task progression
- `workflow.run.created`
- `workflow.run.state_changed`
- `task.run.created`
- `task.run.state_changed`

### Human task lifecycle
- `task.created`
- `task.claimed`
- `task.lease_expired`
- `task.completed`

### Artifact and pointer lifecycle
- `artifact.version.created`
- `artifact.pointer.promoted`
- `artifact.pointer.drift_detected`

### Approval lifecycle
- `approval.requested`
- `approval.responded`
  - payload includes `response` and canonical `outcome`

### Flag lifecycle
- `flag.created`
- `flag.state_changed`

### Execution facet
- `execution.session.created`
- `execution.session.state_changed`
- `tool.execution.requested`
- `tool.execution.approved`
- `tool.execution.denied`
- `tool.execution.completed`

### Projection and health
- `projection.rendered`
- `projection.coherence_failed`
- `audit.degraded_mode.changed`

## 4) Event inventory policy
Workflow contracts now distinguish:
- `event_inventory.platform_required`
- `event_inventory.workflow_required`

`platform_required` means the platform must know and emit the event type whenever relevant.
`workflow_required` means the workflow specifically depends on that event class as part of its executable semantics.

## 5) Required link targets
The envelope's `links[]` model should be able to link to at least:
- workflow_contract_version
- decision_catalog_version
- execution_profile_version
- execution_spec
- workflow_run
- task_run
- human_task
- execution_session
- approval
- artifact_version
- pointer
- tool_execution
- projection
- flag
- policy_decision

## 6) Payload schemas
Each canonical event type should bind to a payload schema in `schemas/events/payloads/`.
The event-type registry is the authoritative index that maps event IDs to required link targets and payload schema paths.

## 7) Authoritative vs advisory events
Authoritative events are those needed to reconstruct official state, lineage, decisions, task ownership, and execution gating.

Advisory planning events may exist later, but they must never be the only record of a state-changing action.

## 8) Cursor / activation semantics
The portable envelope does not force a storage-specific sequence number, but the runtime/export layer should still provide a monotonic consumer cursor per scope.

That means consumers should be able to progress using an ordered position stronger than timestamps alone.

## 9) Conditional task spawning rule
Stage 4 does **not** add a separate `task.spawned` event class.

Instead:
- the parent completion is recorded with `task.completed`
- each spawned child task run is recorded with `task.run.created`
- each spawned claimable work item is recorded with `task.created`

No implicit branching is allowed.
If a task completion causes new work, the new work must be visible through the standard task event classes plus causal lineage (`causation_id`, `spawned_from_task_run_id`, `spawn_rule_id`, or equivalent).

## 10) Degraded mode rule
If an indexer, exporter, cache, or renderer is degraded:
- authoritative timeline writes still succeed
- artifact writes still succeed
- approvals and pointer updates still record normally
- degraded mode becomes visible through explicit events and alerts

## 11) Registry
See `schemas/events/event_type_registry.yaml` for the authoritative event-type registry.

## 12) Command receipts vs event idempotency
Canonical command-boundary retries are command-scoped, not raw-event-scoped.

- canonical CLI/API mutation commands persist a scoped `command_receipt`
- a same-scope retry with the same request replays the committed success and sets `idempotent_replay=true`
- a same-scope retry with a different request fails closed as `command_receipt_mismatch`
- reusing the same client `idempotency_key` across different command scopes is allowed

`timeline_events.idempotency_key` remains an internal append guard.

- it still protects raw event writes from duplicate append
- it still backs `events append`, which continues to fail explicitly with `duplicate_idempotency_key`
- public mutation handlers should normally satisfy retries at the receipt layer before a second event append is attempted
