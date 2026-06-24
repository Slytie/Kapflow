# CAPEX SourceRef And Closure Guardrails

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner tasks: `TASK-0392`, `TASK-0393`, `TASK-0564`, `TASK-0565`
- Scope: internal CAPEX runtime foundation only.

This note records the repo-native guardrails for the first physical source-occurrence and closure-governance primitives. It does not activate CAPEX runtime/product behavior, import raw corpus material, add public APIs, add frontend routes, or approve production/pilot readiness.

## SourceRef Runtime
`capex_content_identities` records digest-based content identity within tenant/domain scope. It is content identity metadata, not a raw document store.

`capex_source_occurrences` records sanitized source occurrences within tenant/domain and optional project scope. A source occurrence may point at sanitized fixture manifests or approved aggregate evidence, but it must not contain raw corpus paths, extracted filenames, screenshots, OCR text, or embedded document content.

The canonical SourceRef format introduced by `TASK-0564` is:

```text
source_occurrence:{source_occurrence_id}
```

The resolver must return an unresolved result for malformed refs, missing occurrences, tenant/domain/project mismatches, and occurrence statuses that are not resolvable. The first resolvable status is `available`; quarantined, redacted, superseded, and deleted occurrences cannot support official claims.

Empty `source_refs` arrays and presence-only evidence are not meaningful evidence.

Source occurrence relations are now internal runtime state only. `TASK-0392` adds `capex_source_occurrence_relations` for same tenant/domain/project duplicate, archive, derivative, and redaction relation rows; both referenced occurrences must already be project-scoped to the same CAPEX project. Public relation commands, locator-union commands, evidence binding, workpage activation, and official pointer effects remain inactive. This relation posture cannot authorize CAPEX runtime activation, raw corpus import, public routes, reviewed baseline truth, or product activation.

## Closure Runtime
`capex_waivers` records scoped waiver state. Direct source/evidence state remains authoritative; a waiver is never a pass.

`capex_closure_gate_evaluations` records vector evaluation. Each required dimension must be satisfied by resolved SourceRefs or explicitly recorded as `satisfied_by_waiver`. Missing evidence leaves the vector failed.

`capex_closure_snapshots` records closure snapshots with a basis version vector. A snapshot can become stale when any basis ref changes or a recurrence rule fires. Stale snapshots must not be treated as fresh closure truth.

The closure result vocabulary is intentionally small:
- `pass`: all required dimensions are satisfied by resolved SourceRefs.
- `satisfied_by_waiver`: every required dimension is satisfied, but at least one dimension used a waiver.
- `fail`: at least one required dimension is missing or unresolved.

## Order-Sensitive Artifact And Closure Formalism
CAPEX artifact, pointer, and closure transitions are non-commutative. The same
source basis change, artifact promotion, or pointer repointing operation can
produce different current-state outcomes depending on whether it occurs before
or after a closure snapshot, official pointer generation, or downstream
commitment is recorded.

Later evidence, artifact ingestion, or pointer activity must not retroactively
rewrite earlier governed outcomes. Instead, later changes must create new
evaluations, pointer generations, stale markers, tasks, approvals, events, or
artifact deltas through the canonical substrate. Historical evaluations,
snapshots, events, and pointer generations remain audit evidence for the order
in which they occurred.

## Rollback Posture
If SourceRef resolution or closure evaluation fails, disable evidence binding and closure gates for the affected CAPEX workflow surface. Do not destroy governed project, source occurrence, waiver, evaluation, or snapshot state as a rollback mechanism.

## Remaining Blockers
The following remain later scope:
- bulk corpus ingest and source inventory pipelines
- source occurrence relations and locator unions with same tenant/domain/project policy
- extraction/search/evidence-binding runtime
- generated artifact envelope and pointer-promotion validators
- public closure/promotion commands, workpages, and frontend UI
- CAPEX runtime/product activation
