# Orchestration semantics

This document is the Stage 4 minimum for durable orchestration semantics.

It exists to prevent an ad-hoc "queue of jobs" implementation that fails under:
- long waits (hours/days)
- retries and worker crashes
- concurrent human or agent actions
- upstream pointer changes (staleness)
- dropped wakeups that must be recovered without duplicating work

The Stage 4 orchestrator is treated as a deterministic state machine driven by authoritative timeline events.

## 1) Formal runtime objects
### WorkflowRun
A long-lived run for a workflow contract version and business partition.

Identity and pinning:
- `(tenant_id, domain_id, workflow_id, partition_key)`
- pinned to:
  - `workflow_contract_version`
  - `decision_catalog_version`
  - `execution_profile_version`
- pinned inputs:
  - the exact artifact version IDs that were official at run start or stage entry
- temporal context:
  - service interval start/end where applicable
  - logical date
  - service timezone

### TaskRun
A stage-scoped run inside a WorkflowRun.
TaskRuns are where:
- stage execution patterns live
- human tasks and approvals bind to exact evidence snapshots
- execution sessions attach
- activation keys are recorded for dedupe

### HumanTask
A work-queue item (candidate roles + claim lease) linked to a TaskRun.

### Approval
A durable decision object linked to:
- a specific action
- the exact evidence snapshot being approved

### ExecutionSession
An execution facet linked to a TaskRun, used for:
- tool calls
- budget accounting
- transcript capture as evidence only

ExecutionSession is not a peer run system.

## 2) Command boundary
The repo should not treat raw event handlers as the authority boundary.

Use this model:

\[
C = \gamma(S_t, e)
\]

Where:
- `e` is one or more authoritative consumed events
- `gamma` is a deterministic decision step
- `C` is a set of canonical commands

Authoritative mutation happens through command execution:

\[
(S_{t+1}, E^{+}, H^{+}) = Commit(S_t, C)
\]

Where:
- `E^{+}` are new authoritative timeline events
- `H^{+}` are after-commit wakeup hints only

Examples of canonical commands:
- `CreateWorkflowRun`
- `CreateTaskRun`
- `EnterWait`
- `RequestApproval`
- `RecordApprovalResponse`
- `CreateArtifactVersion`
- `PromotePointer`
- `MarkStale`
- `ExpireLease`
- `EscalateTask`
- `CompleteTaskAndSpawnFollowOns`
- `ScheduleReconcile`

## 3) Conditional task spawning and dynamic loops
Task completion may produce more work.

Formally, a completion event can drive a follow-on spawn function:

\[
\Delta C_{spawn} = \delta_{spawn}(S_t, e_{task\_completed})
\]

where \(\Delta C_{spawn}\) is a finite set of `CreateTaskRun` and `CreateHumanTask` commands.
This is how Stage 4 supports dynamic loops such as:
- request more information,
- send the work back for changes,
- require final review after a draft is otherwise complete,
- break an issue into additional issue-scoped sub-work.

### Architectural rule
If the parent completion deterministically implies follow-on tasks, the runtime should evaluate the spawn rules inside the same command transaction as the completion.

That means the first implementation should prefer:

If you prefer a plain-text reading:

`Commit(S_t, {CompleteTask} union DeltaC_spawn)`

This keeps the parent completion and any direct child-task creation in one authoritative commit.

over an architecture where child task creation happens only in a later best-effort worker.
The decider/reconciler still exists for:
- flag/timer-driven activations,
- dropped wakeup repair,
- staleness recovery,
- idempotent re-evaluation after failure.

### Guardrails
Dynamic loops are allowed only with:
- explicit authored spawn rules or approved runtime policy
- bounded spawn budgets / max depth
- stable child activation keys
- idempotent child creation

No hidden branching:
- if new work exists, it must appear as `task.run.created` and `task.created`
- if the same logical work is merely reopened or reassigned, reuse the existing task lineage instead of silently creating shadow tasks

## 4) State machines
### WorkflowRun states (MVP)
- `CREATED`
- `ACTIVE`
- `WAITING_HUMAN`
- `WAITING_TIMER`
- `STALE`
- `SUCCEEDED`
- `FAILED`
- `CANCELED`

### TaskRun states (MVP)
- `READY`
- `RUNNING`
- `WAITING_APPROVAL`
- `WAITING_HUMAN_TASK`
- `WAITING_TIMER`
- `STALE`
- `SUCCEEDED`
- `FAILED`
- `CANCELED`

Determinism rule: state transitions depend only on prior state and authoritative input events, not on wall-clock time except through explicit timer / expiry events.

## 5) Stage-scoped eligibility
Do not model readiness as one global workflow predicate.

For stage `j`:

\[
Eligible_j(r,t) = Deps_j(r) \land Inputs_j(r) \land Gates_j(r,t) \land 
eg Stale_j(r)
\]

Where:
- `Deps_j` = predecessor-stage requirements
- `Inputs_j` = required official inputs are present and pinned
- `Gates_j` = approvals, thresholds, or timers are satisfied
- `Stale_j` = a required official pointer moved after the stage snapshot was pinned

### Schedule Planning Stage07
Stage07 is issue-scoped. A better model is:

\[
Eligible_{07,i}(r,t) = PublishedBase(r) \land OpenFlag_i(r) \land ThresholdRule_i(r,t)
\]

Each issue-specific activation should carry an activation key equivalent to:
`(workflow_run_id, flag_id, task_kind, generation)`

## 6) Durable wait model
A wait is not just a state label. It is a persisted blocked-on contract.

Recommended minimum wait descriptor:
- `blocked_on_kind`
- `blocked_on_ref`
- `entered_wait_at`
- `deadline_at`
- `wakeup_cause_event_id` (once resumed)

Examples:
- approval wait
- human-task completion wait
- timer / lease-expiry wait
- external completion wait

## 7) Retry, attempts, and idempotency
Retries occur at:
- event persistence / outbox publish
- projection/index/export consumers
- tool execution
- human or agent double-submit

Policy: at-least-once processing with exactly-once effects via idempotency.

Rules:
- Every authoritative event write must have a stable `event_id`.
- Canonical CLI/API mutation retries resolve through scoped command receipts keyed by `(command_name, scope_key, idempotency_key)`.
- A same-scope retry with the same normalized request must replay the committed success rather than surfacing a duplicate-event error.
- A same-scope retry with a different normalized request must fail closed as `command_receipt_mismatch`.
- Reusing the same client `idempotency_key` across different command scopes is allowed.
- Raw `events append` remains a lower-level event-store operation and still fails explicitly on duplicate `timeline_events.idempotency_key`.
- Every tool execution request must include an `idempotency_key`.
- Artifact version creation must be idempotent by scoped request receipt plus stable event append keys underneath.
- Pointer promotion must be idempotent by scoped command receipt plus canonical pointer-generation checks underneath.
- Child task creation must be idempotent by a parent-cause key such as `(spawn_cause_event_id, spawn_rule_id, activation_key, ordinal)`.

Automated work attempts should track:
- `attempt_no`
- `lease_owner`
- `lease_expires_at`
- `status`
- `error_code`

Do not overwrite the same logical execution row invisibly on retry.

## 8) Reconciliation / sweeper
A reliable orchestrator needs a backstop reconciliation loop even when the fast path is event-driven.

The reconciler should:
- scan for expired leases
- scan for stalled waits or missing wakeups
- re-evaluate eligibility for runs marked ready but not advanced
- recover dropped wakeup hints without duplicating work

The reconciler is a repair mechanism, not a second business logic engine.

## 9) Staleness semantics
A run or task becomes stale when:
- a stage pins input versions at entry
- later, an official pointer for a required dataset key moves
- and the stage semantics care about that input

Staleness must be recorded explicitly:
- `workflow.run.state_changed -> STALE`
- `task.run.state_changed -> STALE`
- `artifact.pointer.drift_detected` when review/promote mismatch is observed

Operator actions for staleness:
- re-run the stage against the new official inputs (new TaskRun)
- explicitly override through the approval model

## 10) Replay, stage rerun, and backfill
These are distinct operations.

- **Retry**: same logical command attempt, same scoped idempotency key, same observable success payload when replayed.
- **Stage rerun**: a new `task_run` inside the same `workflow_run`.
- **Replay**: read-only reconstruction from authoritative history.
- **Historical backfill**: explicit creation of historical workflow runs under separate concurrency controls.

Do not use in-place mutation or implicit run clearing as the recovery mechanism.

## 11) Required timeline evidence per transition
When the orchestrator changes state, it must emit at least:
- `workflow.run.state_changed` for run-level transitions
- `task.run.state_changed` for task-level transitions

Gate objects must emit:
- `task.*` events for work-queue lifecycle
- `approval.*` events for decisions

When task completion creates follow-on work, the timeline must show:
- the parent `task.completed`
- one `task.run.created` per child task run
- one `task.created` per claimable child work item
- causal lineage via `causation_id`, `spawned_from_task_run_id`, or equivalent payload fields

Evidence objects must emit:
- `artifact.version.created` on new versions
- `artifact.pointer.promoted` on official promotion
- `artifact.pointer.drift_detected` when review/promote mismatch is detected
- `flag.created` / `flag.state_changed` when exceptions are surfaced

Execution objects must emit when agentive work is active:
- `execution.session.*`
- `tool.execution.*`

## 12) Deferred concepts (explicitly not MVP)
- general process patch governance
- cross-run migration / in-flight upgrade of workflow logic
- global program runs spanning multiple workflows
