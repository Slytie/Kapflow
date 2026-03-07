# Logistics workflow choices, ambiguities, and possible solutions

This matrix separates:
- choices that must be made **now** for the first next-tranche slice,
- choices that can safely remain staged/deferred.

## 1. Scope of the first logistics test

### Choice
How much of the workflow family should be in the first serious slice?

### Options
1. Weekly planning → live dispatch only
2. Availability request + weekly planning + live dispatch
3. Weekly planning + live dispatch + reporting
4. Full family

### Recommendation
**Option 1**.

### Why
It exercises the core new layer (definitions, control, composition) while avoiding the biggest policy ambiguities.

### Later extension
Add availability request next, then reporting, then timecard audit.

---

## 2. When does `live_dispatch.v1` activate?

### Ambiguity
The docs say live dispatch starts from a daily seed **plus** one or more day-of events.
They do not explicitly say whether Stage07 seed materialization itself creates a live-dispatch run.

### Options
1. **Eager activation**: weekly Stage07 always creates daily live-dispatch runs.
2. **Dormant activation**: weekly Stage07 creates a pending run that wakes when a daily event arrives.
3. **Lazy activation**: first daily event creates the live-dispatch run, provided the seed already exists.

### Recommendation
**Option 3 (lazy activation)** for the first slice.

### Why
It matches the wording most closely and avoids creating empty daily runs for days with no day-of activity.

### Possible solution
- Stage07 emits canonical seed outputs and handoff-ready edge records.
- First valid `dispatch.route_delta_intake.*` or equivalent daily event materializes the live-dispatch activation.

---

## 3. How should the Stage07 seed be represented?

### Ambiguity
The docs say “emit one per-service-day seed artifact,” but the workflow pack still has a single dataset key pair:
- `planning.daily_dispatch_seed.doc`
- `planning.daily_dispatch_seed.workbook`

### Options
1. One batch artifact for the whole week
2. One logical artifact version per `ServiceDateID`
3. One batch artifact plus derived per-day projections

### Recommendation
**Option 2**.

### Why
It aligns with the handoff transform \(PlanningWeekID \to \mathcal P(ServiceDateID)\) and avoids smuggling multi-day semantics into one file identity.

### Possible solution
- Keep the dataset key constant.
- Use `partition_kind=ServiceDateID` and `partition_key=SD-YYYY-MM-DD` for each materialized seed.
- Preserve a provenance edge back to the published weekly schedule.

---

## 4. How should official live operational truth be represented?

### Ambiguity
The docs define:

\[
LivePlan_t = B_t \oplus Delta_t
\]

and say the base seed is immutable and official truth changes only through ordered delta promotion.
But they do not specify whether deltas are:
- a stream of immutable promoted deltas,
- a single current consolidated delta workbook,
- or both.

### Options
1. Single current delta workbook only
2. Ordered stream of immutable delta versions only
3. Ordered stream + derived current-head convenience pointer

### Recommendation
**Option 3**.

### Why
It preserves true history while keeping operator reads simple.

### Possible solution
- `dispatch.official_replan_delta.workbook` becomes a stream-backed official output.
- Keep an ordered sequence field in metadata/provenance.
- Add a compatibility/head pointer if needed for current-board reads.

---

## 5. How should major-replan approval threshold be handled?

### Ambiguity
The docs explicitly say the exact thresholds are “still provisional.”

### Options
1. Hardcode a deterministic placeholder threshold in code
2. Store threshold policy in workflow-family config
3. Treat every dispatch replan as approval-gated initially

### Recommendation
**Option 2**, with a conservative default.

### Why
The threshold is clearly business policy, not engine semantics.

### Possible solution
- Introduce a family-edge or stage policy config such as:
  - route count change threshold,
  - after-confirmation change boolean,
  - no-compliant-candidate trigger,
  - manual override flag.
- Keep the first implementation deterministic and documented.

---

## 6. Should the first candidate ranking use LLM help?

### Ambiguity
The docs allow narrow LLM help for short rationale, but hard filters and core decision logic are deterministic.

### Options
1. Deterministic ranking only
2. Deterministic hard filter + deterministic ranking + optional LLM explanation
3. Deterministic hard filter + LLM-assisted ranking

### Recommendation
**Option 2**.

### Why
It proves the control layer without making the test slice stochastic.

### Possible solution
- Persist the method package for optional rationale generation.
- Keep candidate ordering deterministic in the first slice.

---

## 7. How should issue deduplication be keyed?

### Ambiguity
The live-dispatch docs say activation keys should be `(workflow_run_id, flag_id, task_kind, generation)` “or equivalent.”

### Options
1. Use the exact tuple from the docs
2. Replace with a more semantic issue key immediately
3. Use canonical issue id + stage/task kind + generation

### Recommendation
**Option 1 for the first slice**, unless a canonical issue id already exists in the compiled edge/runtime design.

### Why
This keeps the first implementation close to the authored contract.

### Possible solution
- If a canonical issue id is introduced, persist both for migration/debuggability.

---

## 8. How should approved availability downstream effects work?

### Ambiguity
The docs say approved availability updates may trigger:
- future weekly planning rebuilds, or
- live dispatch review when an already-published day is affected.

But they do not specify the exact decision rule.

### Options
1. Advisory only in first slice (record affected partitions, no automatic activation)
2. Auto-trigger future weekly rebuilds only
3. Auto-trigger future weekly rebuilds + published-day live-dispatch review

### Recommendation
**Option 1 initially**, then move to Option 2.

### Why
The triggering policy depends on calendar, published-state boundary, and operational tolerances that are not fully specified.

### Possible solution
- Compute affected partitions deterministically.
- Emit handoff candidates / notifications, but require explicit operator activation in the first extension.

---

## 9. How should actual-hours feedback into planning/live dispatch be modeled?

### Ambiguity
The docs indicate that dispatch reporting final output should feed future planning and dispatch eligibility, but the exact handoff contract is not formalized.

### Options
1. Treat actual-hours snapshots as direct Stage01 inputs only
2. Add an explicit reporting→planning/reporting→dispatch handoff edge later
3. Model actual-hours as a shared registry now

### Recommendation
**Option 1 for the first slice**, **Option 2 later**.

### Why
The first slice does not need the full reporting feedback loop to prove definitions/control/composition.

### Possible solution
- Use fixture-provided `planning.actual_hours_snapshot.workbook` and `dispatch.actual_hours_snapshot.workbook` in the first slice.
- Add a formal handoff edge from `dispatch_reporting.v1` later.

---

## 10. Should `timecard_audit.v1` be in the first family implementation?

### Ambiguity
It is domain-relevant, but its partition is `PayPeriodID`, not `PlanningWeekID` or `ServiceDateID`.

### Options
1. Include it immediately
2. Delay until partition-transform registry is battle-tested
3. Delay until journal/relation substrate is richer

### Recommendation
**Option 2**, trending toward Option 3 if the first slices surface more ambiguity than expected.

### Why
Timecard audit is valuable, but it does not help prove the first handoff edge as directly as weekly→live does.

---

## 11. How should partition identity be handled?

### Ambiguity
The docs name `PlanningWeekID`, `ServiceDateID`, and `PayPeriodID`, but they do not define a shared machine-readable transform registry.

### Options
1. Keep partition identity stringly typed
2. Add a thin typed partition codec/registry now
3. Add a full business-identity ontology now

### Recommendation
**Option 2**.

### Why
The week→day and service-day→pay-period transforms are first-order concerns for this tranche.

### Possible solution
- Add a small partition registry with codecs, validation, and transform functions:
  - `PlanningWeekID`
  - `ServiceDateID`
  - `PayPeriodID`

---

## 12. How should draft vs official state be separated?

### Ambiguity
The docs are clear conceptually, but not every artifact map makes the draft/official distinction structurally explicit.

### Options
1. Share one namespace and distinguish by artifact role only
2. Use separate registry kinds / stream semantics for draft vs official
3. Use separate dataset keys everywhere

### Recommendation
**Option 2**.

### Why
It keeps the authored packs readable while preventing draft state from being confused with official truth.

### Possible solution
- Preserve dataset keys.
- Distinguish official vs draft by registry kind / promotion boundary / activation state.

---

## 13. How should external connector ingestion be treated?

### Ambiguity
The workflow docs assume normalized artifacts, but do not define connector trust-boundary semantics.

### Options
1. Treat connectors as ordinary modules in the first slice
2. Use fixtures only in the first slice; defer real connectors
3. Implement real connector ingestion before any family work

### Recommendation
**Option 2**.

### Why
Connector trust boundaries are a separate authority problem and would blur the tranche.

### Possible solution
- Use fixture-based normalized inputs for the first slice.
- Add connector modules later with explicit source attestation/quarantine semantics.

---

## 14. How should method packages be pinned?

### Ambiguity
The control layer needs durable semantics, but the exact authored surface is still a design choice.

### Options
1. Pin prompt text only
2. Pin prompt + tool profile + output schema + lowering rules + stop policy
3. Pin full runtime/container digest immediately

### Recommendation
**Option 2** now.

### Why
That is enough to make behavior materially replayable without overcommitting to backend-container details too early.

### Possible solution
- `METHOD_PACKAGE.yaml` authored file
- compiled digest over:
  - prompt/program ref
  - context builder ref
  - tool profile ref
  - structured output schema ref
  - lowering rule ref
  - stop/replay policy ref

---

## 15. How should invariants be referenced?

### Ambiguity
The next tranche needs legality hooks, but not a full invariant kernel.

### Options
1. Use informal invariant names only
2. Use versioned/digested invariant identifiers
3. Build the full invariant algebra now

### Recommendation
**Option 2**.

### Why
This avoids reinterpretation of accepted history later.

### Possible solution
- compiled module definitions reference invariant IDs with version or digest.
- actual invariant engine can remain narrow and staged.

---

## Summary recommendation

For the first next-tranche slice:
- choose **weekly planning → live dispatch**,
- use **lazy live-dispatch activation**,
- model seeds as **one per `ServiceDateID`**,
- model replan deltas as **ordered stream + current-head convenience**, 
- keep ranking **deterministic with optional LLM rationale only**,
- add a **typed partition registry**,
- keep connectors **fixture-only**,
- treat availability/reporting/timecard as staged follow-ons.
