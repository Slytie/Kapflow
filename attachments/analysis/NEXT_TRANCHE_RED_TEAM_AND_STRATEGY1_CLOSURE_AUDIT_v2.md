# Next tranche red-team + Strategy A′ closure audit (updated repo)

Date: 2026-03-07

## Executive conclusion

The rewritten next tranche is directionally correct **if and only if** it is treated as a **definition / control / composition** layer over the **existing Strategy A′ seam**, not over an imagined fully-canonicalized state substrate.

The updated repo materially improves Strategy A′ closure:

- demo/pilot runs succeed,
- same-scope cross-run pointer targets now resolve in workspace/export reads,
- promotion validation now distinguishes scope mismatch from governance-local checks,
- provenance DAG capture and input-binding capture are present.

However, the repo is **not yet a fully fixed post–Strategy A′ substrate** in the strictest sense. Four substrate-critical mismatches remain:

1. authoritative `artifact_pointers` identity is still structurally `(workflow_run_id, pointer_key)`;
2. emitted pointer events still publish `pointer_key` as `pointer_id`;
3. public pointer/read surfaces remain run-local;
4. several planning/architecture docs still describe the old run-local canonical identity.

So the next tranche should proceed only as a **monotone extension over the Strategy A′ compatibility seam**, while explicitly *not* reopening state identity.

---

## 1. First-principles red-team of the rewritten architecture

### 1.1 What problem the next tranche must solve

After Strategy A′, the substrate should already own:

- immutable artifact versions,
- audited registry/pointer movement,
- provenance DAG edges,
- exact input bindings,
- workflow/task/execution activations.

Let

\[
\Omega_1 = (\mathcal V,\mathcal R,\mathcal E,\mathcal P,\mathcal I,\mathcal A)
\]

where:

- \(\mathcal V\): immutable versions,
- \(\mathcal R\): current-state registry,
- \(\mathcal E\): append-only events,
- \(\mathcal P\): provenance DAG,
- \(\mathcal I\): exact input bindings,
- \(\mathcal A\): activation objects (`workflow_runs`, `task_runs`, `execution_sessions`, ...).

The next tranche should add:

\[
\Omega_2 = (\Omega_1,\mathcal D,\mathcal C,\mathcal H)
\]

where:

- \(\mathcal D\): compiled definitions/interfaces,
- \(\mathcal C\): control/method semantics,
- \(\mathcal H\): handoff/composition execution state.

That is the correct formal split because it preserves the difference between:

- **what authoritative state exists**,
- **how modules declare they interact with it**,
- **how methods are evaluated**, and
- **how activations are composed**.

### 1.2 Why the typed reference algebra is better than a new flat global tuple

The rewritten tranche replaces the previously proposed flat logical address with:

\[
StateRef = RegistryRef \;|\; JournalRef \;|\; RelationRef
\]

This is the right move.

A single flat address tuple is mathematically tempting, but it collapses distinct state laws into one carrier. That is brittle because these state classes obey different operational laws:

- `RegistryRef`: current-state / CAS / singleton-or-stream officialness,
- `JournalRef`: append-only posting/order semantics,
- `RelationRef`: graph/validity semantics.

Those are not mere “tags”; they are different algebras. A coproduct of typed references is therefore more faithful than one giant product tuple.

### 1.3 Why not just keep using pointer addresses everywhere?

Because the next tranche needs to support more than one authoritative state discipline in the long run.

If module definitions were expressed only in terms of `PointerAddress`, then journal and relation semantics would later require a second conceptual rewrite.

So the better long-term move is:

- keep `PointerAddress` as the concrete carrier for `RegistryRef`,
- reserve `JournalRef` and `RelationRef` now as typed semantic variants,
- runtime-back only `RegistryRef` at first.

That is the most durable/elegant compromise.

### 1.4 The main remaining architectural risk in my rewrite

The biggest residual risk is this:

The rewrite assumes a “fixed substrate,” but the updated repo still exposes the Strategy A′ state seam in a **mixed** form:

- canonical logical fields exist,
- but authoritative storage and many public read models remain legacy-run-local.

So the next tranche must be careful not to treat:

\[
PointerId \equiv \text{publicly canonical everywhere}
\]

because in the current repo that is false.

The safest interpretation is:

\[
\text{PointerAddress / PointerId} = \text{canonical logical seam}
\]
\[
\text{artifact\_pointers PK + public routes + event payloads} = \text{legacy compatibility carriers}
\]

That distinction needs to be explicit in the tranche plan.

### 1.5 Additional refinement needed for maximal elegance

The rewritten tranche is good, but one refinement would make it cleaner:

In addition to `StateRef`, define the execution/composition side explicitly as something like

\[
ExecRef = ActivationRef \;|\; HandoffRef
\]

because composition semantics are not only about reading/writing state; they are also about routing outputs and acknowledgements between activations.

Without that, there is a temptation to overload `StateRef` for workflow-family handoff state. That would be a design smell.

### 1.6 Formal recommendation after red-team

Keep the rewritten tranche as:

\[
(\Omega_1,\mathcal D,\mathcal C,\mathcal H)
\]

grounded on:

- `RegistryRef(PointerAddress, RegistryKind)` as the only runtime-backed state ref initially,
- explicit activation/handoff state in \(\mathcal H\),
- fail-closed compilation,
- full method-package pinning,
- no new state-plane identity migration.

---

## 2. Updated repo audit: is Strategy A′ closure actually complete?

### 2.1 What *is* clearly complete or materially present

The updated repo **does** show meaningful Strategy A′ closure work:

- `src/onetruth/domain/pointer_address.py` exists and provides:
  - `PartitionRef`
  - `PointerAddress`
  - `PointerId`
  - `RegistryKind`
  - `resolve_legacy_pointer_address(...)`
- `src/onetruth/infrastructure/repositories/artifact_provenance.py` exists and implements:
  - typed artifact provenance DAG edges,
  - cycle detection,
  - legacy lineage projection compatibility.
- `src/onetruth/infrastructure/repositories/input_bindings.py` exists and implements:
  - `workflow_run_inputs`
  - `task_input_bindings`
  - exact pointer/artifact binding capture.
- workspace/export cleanup was added so same-scope cross-run artifact targets resolve correctly in demo-facing outputs.
- promotion validation now checks canonical scope match and raises `artifact_scope_mismatch` when appropriate.
- `docs/planning/STRATEGY_A_CLOSURE_REPORT.md` exists and documents the closure pass.

I also verified directly in the updated repo that:

- `python3 scripts/validate_repo.py --schemas-only` passes,
- the demo command `scripts/run_schedule_workspace_demo.py --scenario stage06_publish_ready ...` succeeds,
- targeted new tests for cross-run same-scope workspace/export resolution pass.

### 2.2 What is **not** fully closed

Despite the closure report saying “ready for monotone extension,” the substrate is still not fully fixed in the strict canonical sense.

#### (a) Authoritative pointer storage is still run-local

`src/onetruth/infrastructure/db/models.py` still defines:

- `ArtifactPointer` primary key = `(workflow_run_id, pointer_key)`,
- uniqueness = `(workflow_run_id, scope_kind, scope_ref, artifact_kind)`.

The raw SQLite substrate in `src/onetruth/infrastructure/events/event_store.py` mirrors that.

So the authoritative row-level registry identity is still legacy-shaped.

#### (b) Repository read functions are still legacy-shaped

`src/onetruth/infrastructure/repositories/artifact_pointers.py` still centers:

- `get_pointer(connection, workflow_run_id, pointer_key)`
- `list_pointers_for_workflow_run(connection, workflow_run_id)`

and those selectors do not return the canonical identity fields by default.

#### (c) Public pointer routes are still run-local

`src/onetruth/api/routes/pointers.py` still filters primarily by:

- `workflow_run_id`
- `scope_kind`
- `scope_ref`
- `artifact_kind`

It does **not** yet expose canonical filtering by dataset/partition/pointer_id.

#### (d) Event payloads still emit legacy pointer identity

In `workflow_task_lifecycle.py`, `artifact.pointer.promoted` still emits:

```json
{
  "pointer_id": pointer_key,
  "dataset_key": artifact_kind,
  ...
}
```

So the event fabric still publishes legacy pointer identity, even though canonical `PointerId` is being computed and stored on the row.

#### (e) Several docs still describe the old canonical identity

At least these docs still describe pointer identity as run-local canonical truth:

- `docs/architecture/promotion_semantics.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- likely parts of `docs/planning/EVENT_EMISSION_MATRIX.md`

So the repo still contains contradictory substrate descriptions.

### 2.3 What that means

There are two possible definitions of “Strategy A′ closure complete”:

#### Strong closure
All authoritative storage, event identity, public reads, and docs agree on the canonical registry identity.

By this definition: **not complete**.

#### Practical closure for the next tranche
The Strategy A′ seam exists, demo-facing surfaces are coherent, historical capture is present, and the next tranche can be layered over the seam without reopening identity migration.

By this definition: **complete enough**, but only if the next tranche respects the seam and does not assume the remaining legacy carriers are already canonical.

That is the correct interpretation of the updated repo.

---

## 3. Implications for the next tranche

### 3.1 Safe assumption

Safe to assume for the next tranche:

- `PointerAddress` / `PointerId` are the **logical canonical registry reference seam**.
- provenance DAG + exact input capture are available.
- demo-facing current-state reads are compatible with same-scope cross-run targets.

### 3.2 Unsafe assumption

Unsafe to assume for the next tranche:

- public pointer APIs already expose canonical identity,
- event replay keyed by `payload.pointer_id` is already canonical,
- `artifact_pointers` row identity is no longer run-local,
- docs fully reflect the new substrate.

### 3.3 Resulting architectural rule

The next tranche should treat the current repo as:

\[
\text{canonical logical seam} \;+\; \text{legacy compatibility carriers}
\]

and therefore should:

- compile module read/write declarations against `StateRef`,
- runtime-adapt `RegistryRef` through the existing `PointerAddress` seam,
- avoid depending on run-local public pointer APIs,
- avoid treating current pointer events as a canonical registry event stream,
- keep journal/relation refs definition-time only until their runtime substrate exists.

---

## 4. Final recommendation

### Go / no-go

**Go**, but with a precision condition:

Proceed with the rewritten tranche only as a **definition / control / composition extension over the Strategy A′ seam**, not as a layer that assumes full state-plane canonicalization has already reached storage/events/public APIs.

### Small pre-tranche cleanup backlog to keep explicit

Before or alongside early next-tranche work, keep this mini-backlog visible:

1. canonicalize emitted pointer event identity,
2. expose canonical pointer reads in repository/API surfaces,
3. finish doc truth-alignment for pointer identity,
4. eventually remove authoritative dependence on `(workflow_run_id, pointer_key)`.

Those should remain clearly scoped as **substrate closure debt**, not be silently absorbed by the next tranche.

### Most important architectural sentence

The most intelligent long-term architecture is:

> keep the authoritative state substrate singular,
> express heterogeneous future state interactions through a typed reference algebra,
> and layer definition/control/composition over that substrate without performing a second identity migration.

That remains the best durable and flexible approach.
