# CAPEX Interface Burden Policy

## Purpose

Interface responsibility must not disappear during CAPEX workflow, workpage, or snapshot handling.

An interface obligation is conserved only when it is exactly one of:
- `owned`: an in-scope actor owns the obligation.
- `transferred`: responsibility moved to a named receiving actor and creates a follow-up acceptance task spec.
- `waived`: an explicit waiver record is referenced.
- `accepted_residual`: an explicit residual-risk acceptance reference is present.
- `open`: the obligation remains unresolved and creates a follow-up task spec.

This policy is an internal validation/prototype layer. It does not create tasks, expose HTTP routes, add frontend surfaces, import raw corpus material, or activate CAPEX runtime behavior.

## Basis Rules

Closed or closure-like responsibility states must carry traceable basis refs. At minimum, the basis must include a `source_occurrence:*` ref or an evidence ref such as `artifact_version:*`, `closure_gate_evaluation:*`, `closure_snapshot:*`, `task_run:*`, `timeline_event:*`, or `waiver:*`.

Open obligations do not need closure evidence, but they must carry a follow-up owner so the work remains visible. Transfers also produce a deterministic `capex.interface_transfer_acceptance` follow-up task spec for the receiving actor.

## Runtime Boundary

The internal helper `onetruth.capex_platform.interface_burden` validates responsibility state and returns deterministic follow-up task specs as data. Later workflow and workpage tasks may convert those specs into canonical human tasks through existing command boundaries. This slice intentionally does not create a second task system.

## Gate Mapping

- `NU-GATE-009`: Interface burden cannot disappear.
- `TASK-0569`: Adds the internal policy helper, docs, and tests.
- Dependency posture: Source occurrence and closure/waiver primitives from `TASK-0564` and `TASK-0565` remain the basis boundary.

## Rollback Posture

If the policy fails, block interface closure or handoff trust and leave CAPEX runtime activation disabled. Do not delete governed project, source, artifact, waiver, closure, or task evidence as a rollback mechanism.
