# Human task semantics

Human tasks are the routing and work-allocation layer around workflow steps and approvals.

## 1) Canonical human-task object
A human task should capture:
- `human_task_id`
- `task_kind`
- `workflow_run_id`
- `task_run_id`
- scope
- candidate roles and optional owner role
- optional assignee actor
- state
- `due_at`
- `escalation_at`
- claim / lease metadata if claimable
- linked approval ID if the task prepares or routes an approval
- linked artifact / flag refs
- reopen count and generation if relevant

## 2) Task kinds
Stage 4 needs only a few:
- `work_item`
- `approval_prep`
- `exception_triage`
- `review_packet`
- `information_request`
- `final_review`

## 3) States
Recommended canonical states for Stage 4:
- `OPEN`
- `CLAIMED`
- `IN_PROGRESS`
- `WAITING_APPROVAL`
- `WAITING_EXTERNAL`
- `ESCALATED`
- `COMPLETED`
- `CANCELED`
- `STALE`

## 4) Claim and lease
If a task is claimable, it must use a lease.

### Claim rules
- Claim is an atomic transition from `OPEN` to `CLAIMED`.
- Claim must carry an idempotency key.
- Only one active claim lease may exist at a time.
- The task stores `lease_version`, `claimed_by`, `claimed_at`, and `claimed_until`.

### Heartbeat / extension rules
- Lease extension must reference the current `lease_version`.
- A successful extension increments `lease_version` and pushes `claimed_until` forward.
- Heartbeats that arrive after lease expiry must fail closed and require reopen or reassignment.

### Expiry rules
- On expiry, emit `task.lease_expired`.
- The current Stage 4 slice chooses reopen-same-row recovery with visible evidence; silent indefinite ownership remains forbidden.

## 5) Candidate roles, owner, assignee
Keep these distinctions explicit:
- `candidate_roles`: who may claim the task
- `owner_role`: who is accountable for outcome if the task stalls or must be escalated
- `assignee_actor`: who currently owns the active lease

### Capability lattice freeze
This repo freezes one capability lattice before any write-path hardening lands.

| Capability | Canonical fields / surfaces | Frozen semantics | Current posture |
|---|---|---|---|
| Routing | `candidate_roles`, `owner_role`, `required_role` | Routing metadata decides candidate pools and accountability. `candidate_roles` gate human-task claim and act as approval fallback responder eligibility when `required_role` is absent. `owner_role` is accountability/escalation metadata only. `required_role` is the authoritative approval responder role when present. | Canonical command/API/scenario paths now require explicit `actor_roles` for role-gated writes; deeper route/hotspot cleanup remains future work. |
| Claim | human task `OPEN` state, `candidate_roles`, lease fields | Claim requires an in-scope actor, an open unassigned human task, and a candidate-role match when candidate roles are present. Successful claim creates the assignee and active lease. | Enforced at the canonical write boundary with explicit forbidden vs conflict semantics (`task_claim_forbidden` vs `task_not_claimable`). |
| Complete / act | claimed human task, assignee, task requirements | Completion is assignee-based. Once a valid claim exists, completion depends on the current assignee and satisfied requirements, not on re-checking `candidate_roles`. | Enforced at the canonical write boundary with explicit assignee/principal denial (`task_complete_forbidden`) separate from requirement/state conflicts. |
| Execute | specialized Stage06 / Stage04 actions, policy decisions, assignee, `stage_id`, `task_kind` | Execute is distinct from claim and complete. It requires the current assignee, the correct stage/task kind, and policy allow or approval-mediated progression through the canonical execution path. | No generic `task.execute` action is introduced in this tranche; specialized execute flows still keep their existing evidence-producing deny path. |
| Collaborate / upload | subject upload endpoints, `artifact.upload` | Upload is collaboration/evidence ingress, not claim, completion, approval response, flag transition, or officialization. | Shared HTTP upload accepts request bytes only (`TASK-0081`), while collaboration upload remains intentionally broader than claim/respond/flag transition at the write boundary. |
| Approval respond | approval `required_role`, approval `candidate_roles`, `approval.respond` | `required_role` governs who may respond when present; otherwise approval `candidate_roles` are the fallback responder pool. | Enforced at the canonical write boundary with explicit forbidden vs conflict semantics (`approval_respond_forbidden` vs `approval_not_respondable`). |
| Flag transition / override | flag state machine, `flag.resolve`, explicit approvals, `task.lease_expired` | Flag transition is separate from task claim/respond semantics. Override and escalation must travel through explicit approvals or visible lease-expiry evidence, not through routing hints alone. | Enforced at the canonical write boundary with explicit forbidden vs lifecycle-conflict semantics (`flag_transition_forbidden` vs illegal/conflict transitions). |

- `candidate_roles` do not by themselves authorize completion, specialized execute actions, uploads, or overrides.
- `assignee_actor` anchors completion and any specialized execute attempt that operates through the same task row.
- The current Stage 4 lease-expiry policy is reopen-same-row with canonical `task.lease_expired` evidence rather than an implicit escalation child task.
- Write-boundary capability enforcement is now implemented for claim, complete, confirm-review, approval response, and flag transition by `TASK-0080`; upload-boundary cleanup is implemented separately by `TASK-0081`.

## 6) Reopen, reassign, escalate, or spawn a new task
### Reopen
Use reopen when the work should return to the candidate pool, usually after lease expiry or stale evidence.

### Reassign
Use reassign when responsibility changes but the work item remains logically the same.

### Escalate
Use escalate when a policy, SLA, or no-progress condition requires owner intervention or approval.

### Spawn a new task run
Use a new TaskRun when completion of the current task reveals a new attributable work unit:
- the LLM or human reviewer needs more information from another role,
- the work is complete but now requires a distinct final review,
- the reviewer requests changes and the workflow must create explicit rework,
- a new issue emerges during Stage07 triage.

Do not hide these as silent state flips on the original task.
Completion of a task may therefore emit:
- `task.completed` for the finished human task,
- followed by one or more `task.run.created` and `task.created` events for follow-on work.

These outcomes should be visible through canonical task events and task-run state changes.

## 7) Relation to approvals
Tasks and approvals are linked but distinct:
- a task may gather evidence and route an approval
- an approval decision may create follow-up tasks
- execution-gate approvals can also be routed through the same task model
- approval responses may spawn explicit rework, information-request, or final-review task runs

A task must never become the only durable record of an approval decision.

## 8) Agent-owned work
Agent-owned work is a mode of the same task system, not a separate universe.

That means:
- the actor type may be `agent`
- the same task states and lease rules still apply
- the same approvals still apply
- the same task / task-run events still apply
- agent completion may spawn follow-on tasks, but only through the same canonical task-run creation path

In debug tenants, designated agent principals may claim and complete tasks through the same canonical task path.

## 9) Conditional follow-on spawning rules
Dynamic loops are allowed, but they must be explicit and bounded.

Required rules:
- follow-on task creation must be caused by an authoritative event such as `task.completed`, `approval.responded`, `flag.created`, or `task.lease_expired`
- the created child task run must stay inside the same `workflow_run_id`
- the child task must carry parent lineage (`spawned_from_task_run_id`, `spawn_rule_id`, or equivalent)
- retries of the same parent completion must not duplicate children
- per-parent or per-issue spawn budgets must exist for workflows that allow loops

Recommended idempotency key shape for a spawned child:
`(parent_completion_event_id, spawn_rule_id, activation_key, ordinal)`

## 10) Schedule Planning nuance
Stage07 intraday exception handling often involves multiple issue-specific tasks:
- no-show coverage
- vehicle outage coordination
- delay-cluster triage
- cross-zone override review

Stage05 and Stage06 may also spawn:
- information requests to `fleet_coordinator` or `schedule_planner`
- re-review after changes were requested
- final-review tasks before publish/promotion

These should remain task runs or human tasks within the same workflow-run context rather than becoming a parallel runtime universe.

Each issue-specific task should be deduped by an activation key equivalent to:
`(workflow_run_id, flag_id, task_kind, generation)`

## 11) Required events
The minimum event evidence for human-task behavior is:
- `task.created`
- `task.claimed`
- `task.lease_expired` when relevant
- `task.completed`
- `task.run.state_changed` for task-run waiting / stale / completion transitions

When completion spawns follow-on work, the evidence must also include:
- `task.run.created` for each child task run
- `task.created` for each claimable child work item
- causal lineage via `causation_id`, `spawned_from_task_run_id`, or equivalent payload fields
