# ADR-005 - Strategy A' history-preserving officialness generalization

## Status
Accepted for planning; implementation pending

## Context
The runtime currently stores official artifact state primarily in a run-local form:
- `artifact_versions.workflow_run_id` acts like ownership,
- `artifact_pointers` are keyed by `(workflow_run_id, pointer_key)`,
- multiple read/query surfaces assume run-local officialness.

The repo’s own mathematical and schema documents already state a stronger intended law:
- officialness should be addressable by dataset/partition/scope,
- runs are modeled as pinned to exact inputs,
- lineage and ordered delta semantics are first-class.

A naive in-place pointer generalization would fix only part of the mismatch. It would still leave several later changes non-monotone because they would require reinterpretation of historical state.

## Decision
Proceed with **Strategy A'** rather than the earlier narrower Strategy A.

Strategy A' includes the officialness lift **and** the minimum additional substrate work needed to keep later extensions monotone:
1. canonical pointer identity lifted above `workflow_run_id`,
2. artifact versions gain semantic address fields separate from provenance,
3. typed provenance DAG support is added now,
4. exact input binding capture is scaffolded now,
5. canonical address reserves `stream_key` and `registry_kind`,
6. typed partition discipline is added now,
7. validation is split into governance-local checks and scope-based state checks,
8. backfill ambiguity semantics are defined explicitly now.

## Why
These additions are required because delaying them would force one or more of the following:
- rewriting canonical identities later,
- guessing missing historical data,
- reinterpreting already-accepted historical transitions,
- changing the effective legality model after the fact.

Those are exactly the classes of migration mistakes we want to prevent.

## Consequences
### Positive
- later richer features (invariant kernels, native evaluators, workflow-family handoffs) can be added as monotone extensions,
- current history remains interpretable,
- the repo stays on one truth substrate rather than adding a second state plane,
- current run-centric UX can be preserved through compatibility projections during migration.

### Costs
- Strategy A becomes larger than a pure pointer-key refactor,
- schema blast radius increases,
- new migration and compatibility tests are required,
- backfill must have explicit ambiguity/quarantine handling.

### Non-goals preserved
- no broad UI semantics change yet,
- no full invariant kernel yet,
- no full evaluator/continuation closure yet,
- no full set/sequence/interval runtime yet.
