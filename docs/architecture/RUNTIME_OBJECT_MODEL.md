# Runtime object model

This document names the canonical runtime objects implied by the merged architecture.

## 1) Canonical objects
### WorkflowRun
Business execution instance pinned to:
- workflow version
- scope `(tenant_id, domain_id)`
- business partition
- exact input versions
- temporal context (`logical_date`, interval start/end, timezone where applicable)
- activation key for dedupe

A workflow run may optionally belong to a CAPEX project through `project_id`, but it is never the project identity.

### CapexProject
Durable CAPEX project root scoped by tenant and domain.
It owns stable `project_id`, project key, state, metadata, creator, and timestamps.

### ProjectMembership
Direct actor-to-project role grant.
It records one active role per `(project_id, actor_type, actor_id)` and remains source state for rebuildable authorization projections.

### CapexProjectAuthorization
Derived project authorization read model.
It is rebuilt from active direct membership today, may later incorporate additional policy inputs, and is not authoritative project truth.

### TaskRun
Bounded unit of work inside a workflow run.
A task run may be human-executed, service-executed, or agent-assisted, but it is still part of the same workflow truth system.

Important fields include:
- stage ID
- state
- activation key
- generation
- blocked-on descriptor
- spawned-from refs (flag, task run, or approval)
- `spawn_rule_id` and `spawn_cause_kind`
- `spawn_cause_event_id`
- `spawn_depth` and optional `spawn_budget_key`

### HumanTask
Canonical work-queue item linked to a TaskRun.
It carries candidate roles, assignee, lease metadata, SLA timestamps, and linked approval/flag refs.

### Approval
Canonical decision object.
Kinds include:
- business decision
- execution gate
- future method-change review

There is one approval system, not separate human-decision and agent-decision universes.

### ArtifactVersion
Immutable object produced, imported, or promoted by workflow activity.
Officialness is defined only through explicit pointers or ordered delta semantics.

### Pointer
Audited mutable registry entry that names which immutable artifact version is official for `(dataset_key, partition, scope)`.

### Flag
First-class exception / anomaly / required-attention item.
Flags exist to make operational risk explicit and attributable without hiding it inside documents.

### Projection
Rendered, coherence-checkable view over authoritative objects.
Examples:
- approval packet
- live operations board
- finance finalize packet

A projection is useful but never authoritative by itself.

### ExecutionSession
Optional execution facet attached to a TaskRun when an agentic or service-driven method is used.
It records runtime budgets, model/tool interactions, and evidence references without becoming a parallel workflow system.

### ToolExecution
Discrete tool invocation linked to an execution session and the governing approval/policy context.
ToolExecution should preserve attempt numbers and idempotency keys.

### PolicyDecision
Canonical allow / deny / require-approval result for a guarded tool request.
This keeps execution gating inside the same truth substrate.

### ExecutionSpec
Compiled immutable runtime plan for a concrete run or bounded run segment.
This is authoritative for execution pinning, but still subordinate to the authored source chain.

## 2) Canonical relationships
- one workflow run has many task runs
- one workflow run may have many flags linked to stages, tasks, and evidence
- one CAPEX project may have many workflow runs
- one CAPEX project may have many direct project memberships
- one task run may spawn zero or more child task runs inside the same workflow-run context
- one task run may have zero or one active execution session at a time
- one execution session may have many tool executions
- one approval may gate a workflow transition, task transition, or tool execution
- one projection is rendered from authoritative objects and should be regenerable
- one pointer names which artifact version is official
- one policy decision may govern one guarded tool request

## 3) Objects explicitly not introduced as peer truth systems
Do not import the Stage 3 spike runtime objects literally as a second authority layer.
Examples that must be translated rather than copied verbatim:
- `agent_runs`
- `human_decision_requests`
- transcript-centric state machines

## 4) Minimal state expectations
- workflow runs and task runs need pinned source refs, temporal context, activation keys, and stale-detection hooks
- CAPEX projects need durable project identity distinct from workflow-run identity
- project memberships need direct role, actor identity, grant actor, state, and audit timestamps
- human tasks need candidate roles, lease version, claimed-until, escalation-at, and linked evidence refs
- approvals need evidence refs, actor, due-at, response verb, outcome, and link targets
- execution sessions need budget class, tool policy context, and source/compiled spec linkage
- tool executions need idempotency, attempt number, policy result, and event linkage
- policy decisions need principal, request attributes, and allow / deny / require-approval result
- projections need coherence status and source lineage
- flags need scope, kind, severity, state, and evidence links (no PII in flag payloads)

## 5) Reopen vs reassign vs spawn a new task run
Use the same TaskRun when the logical objective has not changed and the work is merely:
- reclaimed after lease expiry,
- reassigned to a different actor,
- resumed after a short wait on the same evidence boundary.

Spawn a new TaskRun when the workflow needs a new attributable unit of work, for example:
- an information-request loop against another role,
- a re-review after changes were requested,
- a final review after publish-ready evidence exists,
- a new issue-scoped exception loop in Stage07,
- rework forced by approval response, flag, or staleness.

This distinction keeps dynamic loops auditable:
- reopen/reassign stays on the same logical task lineage,
- new review/rework/info loops become explicit child task runs.

## 6) Schedule Planning implication
Schedule Planning stresses this model because Stage07 is event-triggered exception handling rather than a one-shot stage, and Stage05/Stage06 review work may conditionally spawn new follow-on tasks.
The runtime must therefore support:
- repeated issue-triggered task runs under one service-day partition
- ordered delta artifact versions
- approvals only when thresholded conditions trigger them
- conditional child task runs for information requests, re-review, and final review
- live projections that remain linked back to authoritative base + delta artifacts

## 7) Schema rule
The canonical runtime schemas live under `schemas/runtime/`.
Implementation planning should depend on those schemas rather than re-inventing the object model from prose.
