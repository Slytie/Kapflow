# Promotion semantics

Promotion is how mutable officialness is expressed without mutating immutable artifacts.

## 1) Artifact versions vs pointers
Artifacts are immutable.
Pointers are mutable and audited.

Promotion updates a pointer to reference a specific artifact version.

## 2) Approval and promotion are separate
An approval may authorize a promotion, but the promotion itself is a separate recorded action.

This separation matters because:
- the reviewed version may differ from the promoted version
- drift must be visible
- approvals remain evidence, not pointer state

## 3) Drift
If the promoted version differs from the reviewed or expected version, emit `artifact.pointer.drift_detected` (or equivalent) with enough payload to reconstruct:
- reviewed version
- promoted version
- decision ref
- actor
- time

## 4) Pointer types
Stage 4 conceptually needs at least:
- official input pointer
- official output pointer

Future implementations may use one pointer model with roles rather than separate tables.

## 5) Schedule Planning nuance
Schedule Planning intentionally has two official artifact streams:
- Stage06 base publication
- Stage07 replan deltas

The system should not mutate the published base schedule in place after publication.
Instead:
- Stage06 publishes the base plan
- Stage07 promotes explicit delta artifacts that supersede assignments operationally without erasing the base artifact

The operative live-day view is therefore reconstructed from base + ordered deltas.

## 6) Payroll nuance
Payroll mostly uses straightforward input/output promotions, but the same laws apply:
- exact version recorded
- drift visible
- lock and finalize stages remain explicit and attributable

## 7) Minimum payload expectations
Promotion-related events should include:
- pointer ID
- promoted artifact version ID
- prior pointer target if any
- dataset key
- partition key
- workflow and stage context
- linked approval if present
- drift details if applicable
