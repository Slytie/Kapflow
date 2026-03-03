# RUNTIME_BOOTSTRAP.md

This document turns the contract-closed repo into a concrete runtime bootstrap plan. Its job is to remove implementation ambiguity before the first code PR.

## 1) Hard constraints from repo truth

Stage 4 runtime work must preserve the authoritative substrate:

\[
\Omega = (\mathcal O, \mathcal E, \mathcal R)
\]

where:
- \(\mathcal O\) = immutable objects / versions
- \(\mathcal E\) = append-only timeline events
- \(\mathcal R\) = audited mutable registries / pointers

A runtime command therefore cannot be "write state somewhere and maybe emit logs later".
The canonical mutation rule is:

\[
C_t = \gamma(S_t, u_t), \qquad
(S_{t+1}, E_t^+) = \operatorname{Commit}(S_t, C_t)
\]

where:
- \(u_t\) is the request / stimulus,
- \(S_t\) is canonical current state,
- \(E_t^+\) is the set of authoritative timeline events appended in the same commit.

Stage 4 must also preserve these repo-level constraints:
- one workflow/task/approval/event truth system
- Schedule Planning is the first runtime wedge
- generated artifacts remain downstream
- no external workflow engine becomes a second durable workflow-definition surface
- tests/traces remain the first behavioral harness

## 2) Architecture options reviewed

### Option A - External workflow engine as the runtime source of truth
Examples: Temporal, Conductor, Flowable/Camunda-like engines.

**Pros**
- mature WAIT/retry/timer patterns
- built-in worker orchestration
- rich operational tooling

**Cons**
- introduces a second durable workflow-history and/or workflow-definition surface
- makes it too easy for official state to become "whatever the engine thinks" instead of repo-native artifacts/events/pointers
- encourages hiding artifact promotion and approval semantics behind engine adapters

**Stage 4 decision**
- rejected as the primary runtime substrate
- pattern ideas are useful; the engine itself should not become the Stage 4 source of truth

### Option B - Pure append-only event sourcing with no current-state tables
**Pros**
- maximal audit purity
- every read is derivable from history

**Cons**
- slower first delivery
- human-task claims, approval queues, and pointer officialness become operationally awkward if every hot query must reconstruct from replay
- raises complexity for the first runtime wedge before the semantics are proven

**Stage 4 decision**
- rejected as the initial implementation shape
- keep the timeline authoritative, but also maintain canonical current-state tables transactionally

### Option C - Python modular monolith + PostgreSQL + object storage + workers
**Pros**
- one transactional boundary for current-state rows + timeline events
- straightforward local development and migration path
- easiest way to preserve one truth system while still shipping quickly
- clear path to later extraction if needed

**Cons**
- requires discipline around module boundaries
- background jobs and HTTP handlers still need explicit coordination rules

**Stage 4 decision**
- **chosen**

### Option D - Early microservices
**Pros**
- possible future team parallelism
- independent scaling later

**Cons**
- premature distributed transactions
- more outbox/relay complexity before semantics are proven
- too many failure modes for the first vertical slice

**Stage 4 decision**
- deferred until after the Schedule Planning wedge is stable

## 3) Chosen Stage 4 runtime architecture

Stage 4 should be instantiated as:

- **language/runtime:** Python
- **API adapter:** FastAPI-style HTTP boundary (thin adapter; business logic must not live in route functions)
- **ORM / migrations:** SQLAlchemy + Alembic
- **primary database:** PostgreSQL
- **artifact bytes:** pluggable object-store adapter
  - local filesystem adapter for development
  - S3-compatible adapter later
- **background jobs:** in-process workers / separate worker entrypoints using the same codebase and database
- **repo shape:** modular monolith under `src/onetruth/`

This is not a claim that Python is metaphysically required forever.
It is the chosen Stage 4 implementation so the first coding agent does not have to guess.

## 4) Target repo layout

The first runtime scaffold should create these locations:

```text
src/onetruth/
  api/
    main.py
    routes/
    dependencies.py
  application/
    commands/
    handlers/
    services/
  domain/
    models/
    state_machines/
    policies/
  ports/
    repositories.py
    artifact_store.py
    event_stream.py
    projection_renderer.py
  infrastructure/
    db/
      models.py
      session.py
    repositories/
    events/
    artifacts/
    policy/
    generation/
  workers/
    decider.py
    lease_sweeper.py
    projection_worker.py
    export_worker.py
  cli/

alembic/
  versions/

tests/runtime/
```

Output locations:
- real runtime code: `src/onetruth/`
- migrations: `alembic/`
- runtime tests: `tests/runtime/`
- generated derivatives / prototype outputs: `build/generated/`

## 5) Canonical persistence model

The database must carry both:
1. canonical **current-state tables** for hot operational queries, and
2. canonical **append-only timeline events** for reconstruction and derived consumers.

### 5.1 Current-state tables
These tables are the concrete indexed realization of the canonical runtime object model:

- `workflow_runs`
- `task_runs`
- `human_tasks`
- `approvals`
- `artifact_versions`
- `pointers`
- `flags`
- `execution_specs`
- `execution_sessions`
- `tool_executions`
- `policy_decisions`
- `projections`

Practical storage rule:
- keep hot query fields as first-class columns
- keep structured-but-flexible fields in JSON/JSONB where the schemas already have nested objects
- never collapse the canonical objects into one generic “runtime blob” table

Examples:
- `workflow_runs.temporal_context` can be structured JSON
- `task_runs.blocked_on` can be structured JSON
- `task_runs` should also carry direct child-lineage fields such as `spawned_from_task_run_id`, `spawn_rule_id`, `spawn_cause_kind`, `spawn_cause_event_id`, `spawn_depth`, and optional `spawn_budget_key`
- `timeline_events.links` and `timeline_events.payload` can be structured JSON
- `projections.source_refs` can be structured JSON

### 5.2 Authoritative timeline table
Add `timeline_events` as the append-only event table.

Required properties:
- immutable rows
- portable envelope fields preserved
- required links preserved
- payload preserved
- storage-local monotonic ordering stronger than timestamps alone (for example a `sequence_no` / cursor column)

The portable event envelope should stay storage-agnostic, but the runtime table should still provide a monotonic cursor for consumers.

### 5.3 Consumer progress
Add `consumer_cursors` (or equivalent) keyed by consumer identity + scope.

This table is not a second truth system.
It is the durable progress marker for derived consumers reading the canonical timeline.

## 6) Transaction and command rules

All authoritative mutations should go through command handlers, not ad hoc route logic.

Canonical transaction rule:

1. validate scope / authz / policy
2. load and lock the required current-state rows
3. apply the domain/state-machine transition
4. append the required authoritative timeline event(s)
5. commit once

This implies:
- authoritative events must be written in the **same transaction** as the canonical state change
- exporters/notifiers may lag, but they may not be the place where authoritative state changes are first recorded
- if a command cannot append the required event(s), the command has not completed

### Direct-causality spawn rule
If completion of a task or approval deterministically implies follow-on tasks, the first implementation should create those child task rows and their `task.run.created` / `task.created` events in the same transaction as the parent completion or response.

Use the decider/reconciler for:
- flag-driven or timer-driven activations,
- repair after dropped wakeups,
- re-evaluation after explicit stale/lease events.

Do **not** make child task creation a hidden async side effect when it could have been an atomic direct-causality transition.

## 7) Concurrency, idempotency, and locking

Stage 4 needs three layers of protection:

### 7.1 Unique keys / idempotency keys
Use unique constraints for:
- workflow-run activation keys
- task-run activation keys within the right scope
- child-task spawn keys such as `(spawn_cause_event_id, spawn_rule_id, activation_key, ordinal)`
- tool-execution idempotency keys
- pointer uniqueness for `(scope, dataset_key, partition)`

### 7.2 Row-level locking
Use row-level locking for queue-like operations such as:
- human-task claim/reclaim
- approval response when multiple responders race
- pointer promotion on the same `(scope, dataset_key, partition)` target

### 7.3 Advisory / coordination locks
Use scoped coordination locks only where needed for per-run or per-pointer serialization.
Advisory locks coordinate work; they do **not** become the authoritative record.

## 8) Event relay / outbox model

Stage 4 should **not** add a second authoritative outbox table.

Instead:
- `timeline_events` is the canonical event log
- derived consumers advance using `consumer_cursors`
- wakeups may use database notifications and/or polling
- a missed wakeup must be recoverable by cursor polling / reconciliation

In other words:

\[
\text{DerivedConsumerState}_{t+1}
= F\big(\text{DerivedConsumerState}_t, \; E[\text{cursor}_t+1 : \text{cursor}_{t+1}]\big)
\]

where the consumer reads from the canonical timeline, not from a rival event table.

This keeps one truth system while still supporting exports, notifications, projections, and later bus relays.

## 9) Artifact-store design boundary

Artifact bytes and artifact officialness must stay distinct.

- **Blob/object store** holds immutable bytes
- **`artifact_versions` rows** hold authoritative metadata and linkage
- **`pointers` rows + pointer events** define officialness

Operational rule:
- object bytes may be uploaded first
- they do not become official merely because bytes exist
- an artifact version becomes authoritative only when the metadata row and required timeline event exist
- officialness changes only when the pointer move and required timeline event commit

### Schedule Planning reconstruction law
For a service-day partition \(d\):

\[
\operatorname{OperativeSchedule}(d)
=
B_d \oplus \Delta_{d,1} \oplus \Delta_{d,2} \oplus \cdots \oplus \Delta_{d,n}
\]

where:
- \(B_d\) is the Stage06 published base schedule
- \(\Delta_{d,i}\) are ordered Stage07 replan deltas
- \(\oplus\) means apply the delta in authoritative order without mutating \(B_d\)

The order must be reconstructable from authoritative metadata + promotion events, not inferred from a dashboard snapshot.

## 10) Minimal API / worker boundaries

### First API surfaces
Start with command-oriented surfaces for:
- create workflow run
- create / advance task run
- create / claim / complete human task
- complete task and spawn follow-on tasks
- request / respond approval
- create artifact version
- promote pointer
- query run / task / approval / timeline detail
- inspect task lineage / spawned children

### First workers
Start with:
- decider / reconciler
- lease-sweeper
- projection worker
- export / notifier relay

Defer generalized UI, third-party integration fan-out, and multi-service decomposition.

## 11) What should not be written first

Do **not** start by building:
- a generalized workflow designer
- a UI-heavy ops console
- a generalized CompanyOS compiler service
- a cross-workflow abstraction layer more general than the first slice requires
- a microservice split
- a second durable workflow engine

## 12) Immediate follow-on docs/tasks

With the runtime bootstrap chosen, the next planning outputs should be:
- `docs/planning/EVENT_EMISSION_MATRIX.md` (`TASK-0029`)
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` (`TASK-0039`)
- `docs/planning/ARTIFACT_STORE_DESIGN.md` (`TASK-0030`)
- `docs/planning/PROJECTION_COHERENCE_HARNESS.md` (`TASK-0031`)
- `docs/planning/GENERATOR_PROTOTYPE_PLAN.md` (`TASK-0032`)
