# Next tranche rewrite — definition / control / composition extension over a fixed post–Strategy A′ state substrate

## Purpose

This document rewrites the proposed next tranche so it is a **definition / control / composition** extension over a **fixed post–Strategy A′ state substrate**, rather than a second state-plane migration.

It also makes explicit where the current repo still falls short of that assumption, so the tranche can be staged honestly.

---

# 1. Architectural rule

The next tranche must be a monotone extension:

\[
\Omega_2 = E(\Omega_1)
\]

where:

- \(\Omega_1\) is the fixed post–Strategy A′ substrate,
- \(E\) adds new definitions, evaluators, activations, projections, and composition records,
- and \(E\) does **not** reinterpret canonical state identity, past commits, or already-accepted transition legality.

## Consequence

This tranche must **not**:

- redefine canonical officialness identity,
- introduce a new flat address shape that supersedes `PointerAddress`,
- reopen pointer-key migration decisions,
- reinterpret historical event identity,
- fold unfinished Strategy A′ closure work into a broader plugin/runtime rollout.

---

# 2. Fixed substrate contract assumed by this tranche

The tranche assumes the substrate contract below.

## 2.1 Registry/current-state substrate

Canonical registry state is addressed by a Strategy A′ registry coordinate:

\[
RegistryAddress = (tenant, domain, dataset, partition, stream?, registry\_kind)
\]

The concrete implementation seam for the current repo is the existing Strategy A′ pointer-address family:

- `PointerAddress`
- `PartitionRef`
- `PointerId`
- `RegistryKind`

This tranche **builds on top of that seam**. It does not replace it.

## 2.2 Historical continuity is already captured

The tranche assumes the substrate already records:

- immutable artifact versions,
- typed provenance DAG edges,
- exact workflow/task input bindings,
- append-only events,
- audited pointer movement.

So the next tranche can safely add **definition** and **control** abstractions without inventing missing history.

## 2.3 Workflow/task/execution activations remain real

This tranche does **not** delete or demote the current activation objects:

- `workflow_runs`
- `task_runs`
- `human_tasks`
- `execution_sessions`
- `tool_executions`

Instead, it layers definitions and method semantics above them.

---

# 3. Replace the flat `LogicalAddress` proposal with typed state references

The original pack proposed a single flat logical address of the form:

\[
A=(tenant,domain,plane,kind,scope,key,facet,cardinality,valid\_time?)
\]

That is **not** the right next move.

## Why not

Because it risks becoming a second identity migration immediately after Strategy A′. The repo already has a canonical state-address seam for registry officialness. The next tranche should not supersede it with a broader unproven tuple.

## Use this instead

Introduce a typed state-reference algebra:

\[
StateRef = RegistryRef \;|\; JournalRef \;|\; RelationRef
\]

with the first variant grounded directly in the Strategy A′ seam.

### RegistryRef

\[
RegistryRef = (PointerAddress, RegistryKind)
\]

This is the default reference for official current-state interactions.

### JournalRef

\[
JournalRef = (tenant, domain, journal\_kind, partition\_ref, stream\_key?)
\]

This is reserved for append-only posting semantics and does **not** redefine registry identity.

### RelationRef

\[
RelationRef = (tenant, domain, relation\_kind, left\_identity, right\_identity, valid\_time?)
\]

This is reserved for explicit graph/relation semantics.

## Immediate implementation rule

Only `RegistryRef` needs to be runtime-backed in the first serious slice.

`JournalRef` and `RelationRef` may exist at definition/compilation time before their full runtime substrate is implemented.

---

# 4. Revised formal architecture

The next tranche adds three layers over the fixed substrate:

\[
\Omega_2 = (\Omega_1, \mathcal D, \mathcal C, \mathcal H)
\]

where:

- \(\mathcal D\): definitions / compiled module interfaces
- \(\mathcal C\): control / method execution semantics
- \(\mathcal H\): handoff / composition execution state

## 4.1 Definitions layer \(\mathcal D\)

A compiled module definition is:

\[
\widehat M = (\Sigma_{in}, \Sigma_{out}, Q_M, Bind_M, R_M, W_M, F_M, G_M, B_M, P_M, V_M)
\]

where:

- \(\Sigma_{in}, \Sigma_{out}\): typed input/output surfaces
- \(Q_M\): partition / instance algebra
- \(Bind_M\): input-binding and idempotency policy
- \(R_M\): read set over `StateRef`
- \(W_M\): write set over `StateRef`
- \(F_M\): invariant family IDs used by the module
- \(G_M\): governance/authz/approval policy
- \(B_M\): budget/QoS profile
- \(P_M\): method-package references
- \(V_M\): pinned semantic identity / version digest

### Key rule

`R_M` and `W_M` must be expressed in terms of `StateRef`, **not** raw run-local keys.

That is the actual monotone-extension boundary.

## 4.2 Control layer \(\mathcal C\)

A method package is:

\[
P=(\pi,c,\mathcal T,\rho,\ell,\sigma)
\]

where:

- \(\pi\): prompt/program specification
- \(c\): context-builder digest/reference
- \(\mathcal T\): tool profile digest/reference
- \(\rho\): structured output schema digest/reference
- \(\ell\): lowering rules into canonical commands
- \(\sigma\): continuation / stop / replay policy

A runtime activation is:

\[
Act(M) = (M, \rho, I, \mu, \chi, s)
\]

mapped onto the existing activation objects:

- workflow activation → `workflow_runs`
- task activation → `task_runs`
- human activation → `human_tasks`
- method execution → `execution_sessions`
- tool call → `tool_executions`

## 4.3 Composition layer \(\mathcal H\)

A family edge is:

\[
E_{ij}=(\tau_{ij}, h_{ij}, \iota_{ij}, \omega_{ij}, \kappa_{ij})
\]

with:

- \(\tau_{ij}\): partition transform
- \(h_{ij}\): handoff mode
- \(\iota_{ij}\): idempotency/replay policy
- \(\omega_{ij}\): writer mode
- \(\kappa_{ij}\): compensation/failure semantics

### Critical rewrite

Do **not** compile edges into only `consumer_cursors`.

Instead add explicit handoff execution state, e.g.:

\[
EdgeExec = (edge\_id, source\_activation, target\_activation, correlation\_key, idempotency\_key, status, cursor\_state, compensation\_state)
\]

`consumer_cursors` may still exist, but only as a delivery/progress primitive. They are not enough to represent semantic handoff state by themselves.

---

# 5. Authored surface rewrite

The authored surface should remain minimal and repo-native.

## Keep canonical workflow packs at workflow scale

Continue to treat these as canonical workflow-scale authored sources:

- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`
- `ACCEPTANCE_CRITERIA.md`
- `OPERATING_MODEL.md`

## Add only what is needed

### 5.1 Workflow-pack extensions

Add small optional sections that compile into the definition layer:

- module-interface annotations
- state refs over `RegistryRef | JournalRef | RelationRef`
- activation hints
- exported events / APIs
- security scope declarations
- invariant ID references

### 5.2 Reusable task / connector modules

Allow task/connector-scale authored modules to compile into the **same** compiled descriptor class as workflow packs.

Do **not** introduce a second ontology where workflow packs and task modules are fundamentally different species.

### 5.3 Method-package authored surface

Treat behavior-bearing task methods as separately pinned authored artifacts:

- prompt/program ref
- tool profile ref
- output schema ref
- lowering-policy ref
- continuation policy ref
- replay class
- artifact policy
- spawn policy

This keeps stable business/module interfaces separate from evolving execution behavior.

---

# 6. Control-plane rewrite

## 6.1 Enrich `ExecutionSpec`, do not replace it

The repo already has `ExecutionSpec` as a lowering target. Keep that role, but enrich it so it can pin actual behavior semantics.

At minimum, enrich it with:

- `module_id`
- `module_version`
- `activation_kind`
- `task_method_digest`
- `tool_profile_digest`
- `output_schema_digest`
- `context_builder_digest`
- `lowering_digest`
- `continuation_policy_digest`
- `replay_class`
- `artifact_policy`
- `spawn_policy`

## 6.2 Generic task-method executor

Refactor the current specialized Stage06 path into a generic method-execution framework that:

1. loads `ExecutionSpec`
2. resolves the method package
3. constructs context from exact pinned inputs
4. runs the bounded code/LLM/tool step
5. validates structured output
6. lowers only into canonical commands
7. persists continuation state and execution evidence
8. pauses/spawns/waits/finishes through current runtime objects

### Important rule

The method runtime never mutates truth directly.

It may only propose canonical effects such as:

- create artifact version
- promote pointer
- request approval
- request tool
- emit event
- spawn activation
- pause / wait / fail

That preserves the current one-truth boundary.

---

# 7. Composition-plane rewrite

## 7.1 Family graph compiler

Compile workflow/task/connector definitions plus family-graph edges into:

- node registry
- edge registry
- edge-trigger registrations
- partition transforms
- handoff rules
- idempotency templates
- writer modes
- compensation modes

## 7.2 Explicit edge execution records

When an edge fires, create an explicit handoff execution record rather than only advancing a consumer cursor.

That record should pin:

- source event or source activation ref
- target module ref
- derived target partition / activation key
- correlation key
- idempotency key
- write intent summary
- compensation state
- lifecycle state

This is required for replay safety, compensation, duplicate suppression, and auditability.

## 7.3 Fail-closed choreography

If an edge cannot provide replay-safe semantics, it must not be implemented as an automatic cursor-driven consumer.

That is a hard rule.

---

# 8. What is explicitly **not** in this tranche anymore

The following are removed from the tranche and treated as substrate preconditions or later layers:

## Removed from this tranche

- pointer-identity migration work
- artifact-version ownership-to-provenance migration work
- new flat `LogicalAddress` ontology
- state-plane generalization plan phases
- any second state-substrate design

## Deferred but still compatible

- full invariant kernel
- full journal/relation runtime backing
- full native evaluator closure
- richer connector/runtime trust layers beyond first compiled seams

These remain additive once the current substrate is actually fixed.

---

# 9. TDD-first implementation sequence for the rewritten tranche

## Gate 0 — substrate closure check

Before implementation starts, require a closure gate proving:

1. canonical pointer identity is the authoritative identity in events and public contracts,
2. compatibility reads are explicit,
3. stale run-local legality assumptions are contained,
4. docs/schemas are internally consistent.

If this gate fails, do closure work first. Do not blur it into this tranche.

## Phase 1 — definitions compiler

Build:

- compiled module descriptor class
- typed `StateRef` algebra
- workflow-pack compiler extensions
- task/connector module compiler
- family-graph compiler

Tests first:

- compiler round-trip / fail-closed tests
- no-raw-run-local-key tests
- `RegistryRef` compatibility tests
- schema validation tests

## Phase 2 — control closure

Build:

- enriched `ExecutionSpec`
- method-package pinning
- continuation state object/artifact
- generic task-method runner behind the existing execution-session/tool-execution runtime

Tests first:

- `ExecutionSpec` pinning tests
- replay-class tests
- structured-lowering tests
- continuation/idempotency tests
- “no direct truth mutation” tests

## Phase 3 — composition closure

Build:

- edge registry
- edge execution records
- trigger-to-edge materialization
- cursor integration as delivery progress only
- compensation/idempotency state

Tests first:

- edge handoff idempotency tests
- replay-safe retry tests
- duplicate suppression tests
- compensation-state tests
- target activation derivation tests

## Phase 4 — first slice proof

Use one narrow but real slice to prove the architecture, for example:

- workflow module definition
- reusable task method package
- one family edge
- one generic method execution
- one canonical registry write through the fixed substrate

The slice must demonstrate extension, not substrate rescue.

---

# 10. Current repo status vs this rewritten tranche

## Honest reading

The current repo is close enough to justify writing this tranche in the rewritten form, because the right seams exist:

- `PointerAddress` / `PointerId`
- provenance DAG scaffolding
- input binding capture scaffolding
- `execution_sessions` / `tool_executions`
- working demo / pilot

## But

The repo is **not yet closed enough** to implement the tranche as though the substrate were fully fixed.

So the right practical stance is:

### Architecture
Yes — use this rewritten tranche.

### Implementation start
Only after a small closure gate / cleanup pass verifies the Strategy A′ substrate is actually stable enough to depend on.

That keeps the next tranche additive rather than turning it into a stealth second migration.
