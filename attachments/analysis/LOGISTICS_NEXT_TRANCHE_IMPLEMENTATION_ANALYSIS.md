# Logistics workflow as the first serious next-tranche test

## 1. Executive recommendation

Use the logistics family as the first major test of the next tranche, but **not** all at once.

The right first implementation slice is:

\[
\texttt{weekly\_schedule\_planning.v1} \longrightarrow \texttt{live\_dispatch.v1}
\]

with:
- `availability_request.v1` added as the first extension,
- `dispatch_reporting.v1` added after the weekly→live handoff works,
- `timecard_audit.v1` deferred until partition transforms and downstream reconciliation state are stable.

This is the best tradeoff between realism and ambiguity.

---

## 2. Why this is the right domain test from first principles

The next tranche is not a state-plane migration. It is a **definition / control / composition** extension over the post–Strategy A substrate.

Formally, it should add:

\[
\Omega_2=(\Omega_1,\mathcal D,\mathcal C,\mathcal H)
\]

where:
- \(\Omega_1\) is the fixed post–Strategy A state substrate,
- \(\mathcal D\) is compiled definitions,
- \(\mathcal C\) is control / method execution semantics,
- \(\mathcal H\) is handoff / composition execution state.

The logistics family is the best test because it simultaneously exercises:

### A. Definition complexity
The family has multiple authored workflow packs with real structure:
- stages,
- partition semantics,
- execution profiles,
- decisions,
- artifact maps,
- acceptance criteria.

So it is a realistic test of definition compilation rather than a toy pack.

### B. Control-pattern diversity
The family includes all the control patterns we need to prove:

- `linear_chain` in weekly planning, reporting, and timecard audit,
- `approval_gate` in availability request, weekly publish, dispatch major replan, reporting review, and timecard correction review,
- `bounded_exception_loop` in live dispatch Stage02.

A good next-tranche test should not need a second domain just to exercise the control layer.

### C. Composition / handoff semantics
The family contains the most important handoff already stated explicitly in the docs:

\[
\tau_{week\to day}: PlanningWeekID \to \mathcal P(ServiceDateID)
\]

That is the Stage07 weekly-seed materialization handoff into live dispatch.

That one edge alone forces the tranche to handle:
- partition transforms,
- exact input lineage,
- activation policy,
- idempotent handoffs,
- shared official state references,
- and draft vs official separation.

### D. State-shape diversity
The domain also forces us to respect that not all authoritative state obeys the same algebra.

- weekly published schedule is a singleton registry snapshot,
- daily dispatch seed is a per-day registry output,
- live dispatch deltas are an ordered stream,
- reporting closeout is derived/packet state,
- timecard audit is reconciliation state.

So the domain strongly justifies the typed state-reference approach:

\[
StateRef = RegistryRef \,|\, JournalRef \,|\, RelationRef
\]

rather than one oversized flat address tuple.

---

## 3. Why the first slice should be weekly -> live dispatch

### The key reason
It is the cleanest edge in the family.

The docs state:
- weekly planning Stage07 emits one per-service-day seed artifact,
- live dispatch starts from that base seed plus daily operational events,
- and live dispatch official truth is base seed plus ordered deltas.

That means the first slice already tests:
- compiled module definitions,
- activation logic,
- handoff semantics,
- bounded control logic,
- approval escalation,
- and ordered official-output promotion.

### What it avoids
It avoids the two biggest ambiguities in the pack:

1. whether approved availability updates should auto-trigger a planning rebuild or a live-dispatch review,
2. how reporting actuals should formally feed back into planning/live dispatch before a richer relation/journal layer exists.

Those are real extensions, but they should come **after** the primary handoff substrate is proven.

---

## 4. Recommended staged implementation inside the next tranche

## Stage A — Definitions only
Bring the new workflow packs into the repo as canonical authored assets.

Add a small new authored surface above them:
- `WORKFLOW_FAMILY.yaml`

This should describe:
- module membership,
- source workflow pack version,
- family edges,
- partition transforms,
- activation policy,
- writer mode,
- idempotency mode,
- compensation mode.

The compiler should produce compiled definitions, not runtime behavior yet.

### Deliverables
- workflow family schema
- workflow family compiler
- compiled module descriptor schema
- compiled family-edge schema
- contract tests for pack + family validation

---

## Stage B — Control layer over existing activation objects
Do **not** invent a second activation model.

Map the control layer onto existing runtime objects:
- workflow activation → `workflow_runs`
- task activation → `task_runs`
- human activation → `human_tasks`
- method execution → `execution_sessions`
- tool invocation → `tool_executions`

Add method-package pinning and compiled execution metadata, but keep the current activation objects real.

### Deliverables
- method package schema
- compiled stage execution spec
- activation request / activation state schemas
- tests that compiled control metadata can drive existing activation semantics

---

## Stage C — Composition / handoff runtime
This is the first truly new runtime surface.

Do **not** compile family edges into cursors alone.

Add an explicit handoff execution record, e.g.

\[
EdgeExec=(edge\_id,source\_activation,target\_activation,correlation\_key,idempotency\_key,status,cursor\_state,compensation\_state)
\]

The first implemented edge should be:

\[
\texttt{weekly\_schedule\_planning.Stage07} \rightarrow \texttt{live\_dispatch.Stage01}
\]

with partition transform:

\[
\tau_{week\to day}(PW\text{-}2026\text{-}W10)=\{SD\text{-}2026\text{-}03\text{-}02,\ldots,SD\text{-}2026\text{-}03\text{-}08\}
\]

and exact lineage from:
- the published weekly schedule version,
- the generated daily seed version,
- the receiving live-dispatch activation.

### Deliverables
- handoff edge schema
- handoff execution schema
- explicit partition transform registry
- idempotency tests
- replay/recovery tests

---

## Stage D — Minimal logistics scenario harness
Add a new scenario harness and golden slice that proves the definitions/control/composition layer works.

The minimal test fixture should be:

1. create a `PlanningWeekID` weekly-planning run,
2. ingest route horizon + approved availability + actual hours snapshot,
3. approve and publish weekly schedule,
4. materialize daily dispatch seed for one `ServiceDateID`,
5. ingest a daily route delta,
6. create live-dispatch activation from seed + event,
7. run issue triage,
8. require major-replan approval only when configured threshold is met,
9. promote one ordered official replan delta,
10. verify lineage, handoff record, and official state refs.

This should become the first acceptance/golden test for the next tranche.

---

## 5. Exact test matrix for the logistics slice

### Definition tests
- workflow packs validate
- family graph validates
- compiled module definition is deterministic
- compiled family edge is deterministic
- fail-closed when pack data is insufficient

### Control tests
- compiled stage metadata maps correctly onto execution pattern
- method package pins tool profile, output schema, lowering rules, and stop policy
- live-dispatch Stage02 bounded loop respects stop rules
- approval-gate stages require decision refs

### Composition tests
- week→day partition transform is exact and deterministic
- duplicate seed materialization does not duplicate handoff execution
- same seed + same route-delta event does not create duplicate live-dispatch activation
- handoff records survive replay
- promoted delta is linked to exact seed/base version and issue lineage

### Compatibility tests
- current Strategy A substrate remains authoritative
- current schedule demo still runs
- no regression in workspace/export behavior

---

## 6. How this integrates into the tranche task graph

The next tranche should be split into four work blocks.

### Block 1 — Authored definitions
- add workflow family authored surface
- add schemas
- add compiler
- add contract tests

### Block 2 — Compiled control metadata
- add method package authored/compiled surface
- add compiled stage execution descriptors
- attach to current runtime activation surfaces
- add unit/contract tests

### Block 3 — Handoff runtime
- add family-edge execution tables / repositories / handlers
- add partition transform registry
- add idempotency / replay tests

### Block 4 — Logistics scenario slice
- add weekly→live fixture family
- add runtime scenario tests
- add acceptance/golden pack

Availability-request integration should be Block 5, not Block 4.

---

## 7. What should stay out of the first logistics slice

Do not put these into the first serious implementation slice:

- real connector ingestion from Google Form, Amazon email, or EOS exports
- timecard/payroll downstream reconciliation
- full invariant kernel
- full journal/relation runtime substrate
- fully automatic availability-triggered replans
- LLM ranking inside the first live-dispatch candidate selector

These are valid later extensions, but they add ambiguity faster than value in the first proof slice.

---

## 8. Concrete recommendation

### Recommendation
Adopt the logistics family as the next-tranche proof domain, but stage it as:

1. `weekly_schedule_planning.v1` + `live_dispatch.v1` first,
2. `availability_request.v1` next,
3. `dispatch_reporting.v1` after handoff/runtime is stable,
4. `timecard_audit.v1` last.

### Why this is the most durable approach
It maximizes signal on the new architecture while minimizing undocumented policy guesses.

It is also the cleanest monotone extension:
- Strategy A finishes the state substrate,
- this tranche adds definitions, control, and composition,
- later flows add richer state families without forcing a second migration.
