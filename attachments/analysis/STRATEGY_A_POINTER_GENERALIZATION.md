# STRATEGY_A_POINTER_GENERALIZATION.md

Purpose: implementation plan for **Strategy A'** — in-place generalization of official artifact identity so canonical officialness becomes enterprise-scoped without introducing a second truth system.

This document is the implementation companion to:
- `docs/planning/STRATEGY_A_REVIEW_AND_INTEGRATION_ANALYSIS.md`
- `docs/adr/ADR-005-strategy-a-history-preserving-generalization.md`

## 1) Problem statement

The runtime currently behaves approximately like:

\[
\Pi_{current} : (workflow\_run\_id, pointer\_key) \rightharpoonup (artifact\_version, generation).
\]

That makes `workflow_run_id` the accidental universe boundary for business state.

The target model is:

\[
\Pi_{target} : (tenant, domain, dataset, partition, stream?) \rightharpoonup (artifact\_version, generation, registry\_kind),
\]

with workflow/task/approval references retained as provenance and governance context, not canonical state identity.

## 2) Scope of Strategy A'

### In scope now
1. canonical pointer identity lift,
2. artifact version semantic address fields,
3. typed provenance DAG support,
4. exact input binding capture scaffolding,
5. typed partition discipline,
6. reserved stream/cardinality fields,
7. governance-local vs scope-based validation split,
8. explicit backfill ambiguity semantics,
9. compatibility projections for current run-centric read surfaces,
10. TDD-first migration suites and rollout gates.

### Explicitly out of scope now
1. full invariant kernel,
2. full native evaluator/continuation runtime,
3. full workflow-family handoff framework,
4. rich set/sequence/interval execution semantics beyond reserved schema/registry-kind support,
5. broad UI redesign to show enterprise-global state by default.

## 3) Guiding rules

### Rule A — one truth substrate remains
The migration must preserve the existing authority model:
- immutable versions,
- append-only authoritative events,
- audited mutable registries,
- no second truth plane.

### Rule B — no history reinterpretation later
Any capability whose absence would require later guessing or reinterpreting old history must be part of Strategy A'.

### Rule C — branch by abstraction
All runtime code should move through a single address abstraction (`PointerAddress`, `PartitionRef`, `PointerId`, `RegistryKind`) before schema cutover.

### Rule D — expand, migrate, contract
- expand schema first,
- dual-write and backfill next,
- dual-read with compatibility projections next,
- contract/remove-old only after measured stability.

## 4) Canonical concepts to freeze before coding

### 4.1 PointerAddress

\[
A = (tenant, domain, dataset\_key, partition\_ref, stream\_key?)
\]

Where `partition_ref` is typed, not raw folklore.

### 4.2 Pointer identity
A stable `pointer_id` must exist independently of legacy `pointer_key`.

### 4.3 RegistryKind
Minimum reserved kinds:
- `singleton`
- `membership_set`
- `ordered_stream`
- `interval`

Only `singleton` must be fully supported immediately. `ordered_stream` is reserved because Stage07 already points in that direction semantically.

### 4.4 Version address vs provenance
Artifact versions need two different concepts:
- semantic address: where the version belongs in enterprise space,
- provenance: which workflow/task/approval produced or promoted it.

### 4.5 Exact input bindings
Runs/tasks must be able to persist exact consumed inputs.

### 4.6 Provenance DAG
Lineage must support multiple typed input edges, not just unary compatibility fields.

## 5) High-level implementation sequence

### Phase 0 — spec freeze and red-team
Outputs:
- ADR,
- detailed analysis artifact,
- revised intake,
- revised task graph,
- TDD coverage additions.

### Phase 1 — abstraction seam
Outputs:
- `PointerAddress`, `PartitionRef`, `PointerId`, `RegistryKind`,
- legacy resolution rules,
- deterministic failure modes for ambiguous legacy input.

### Phase 2 — schema expand
Outputs:
- canonical pointer/version fields,
- reserved registry kind and stream key,
- typed partition fields,
- provenance DAG tables,
- exact input binding tables,
- parity across SQLAlchemy, Alembic, and bootstrap DDL.

### Phase 3 — dual-write writers
Outputs:
- create-version writes canonical address + provenance DAG compatibility,
- pointer promotion writes canonical pointer identity,
- authoritative execution/promotion paths capture exact input bindings,
- legacy behavior remains unchanged externally.

### Phase 4 — backfill and reconcile
Outputs:
- idempotent backfill tooling,
- ambiguity quarantine/reporting,
- cutover metrics,
- explicit proof that backfill never invents official truth.

### Phase 5 — validation/security split
Outputs:
- governance-local checks kept explicit,
- scope-based state checks added explicitly,
- new negative tests for wrong tenant/domain/partition.

### Phase 6 — dual-read + compatibility projections
Outputs:
- internal reads new-first,
- run/workspace/board/export surfaces still behave run-centrically through compatibility projections,
- canonical filters exposed without broadening user-facing semantics prematurely.

### Phase 7 — contract/remove-old
Outputs:
- fallback reads removed,
- legacy identity assumptions removed,
- validators/docs/tests finalized,
- stale migration codepaths deleted.

## 6) Required test strategy additions

This migration is not done when the code compiles. It is done when the repo can prove:
- canonical identity is correct,
- history remains interpretable,
- ambiguous legacy rows are quarantined rather than guessed,
- compatibility surfaces remain stable while cutover is in progress.

### Required suites
- abstraction/unit tests,
- schema parity tests,
- provenance DAG tests,
- exact input binding tests,
- dual-write equivalence tests,
- backfill ambiguity/idempotency tests,
- compatibility projection contract tests,
- security isolation tests,
- replay and acceptance regressions.

## 7) Release gates

Cutover may proceed only if all are true:
- dual-write drift is at or below approved threshold,
- unresolved ambiguous backfill rows are at or below approved threshold,
- replay/acceptance/security suites remain green,
- current run-centric query contracts remain stable unless explicitly versioned,
- rollback path has been rehearsed.

## 8) Design note: what we are intentionally *not* doing

We are **not** introducing a second enterprise truth subsystem.

Strategy A' is still an in-place generalization of the existing artifact/version/pointer substrate.
The additional pieces (provenance DAG, input bindings, typed partitions, registry kind) are there to make the identity migration history-preserving, not to redesign the entire product.
