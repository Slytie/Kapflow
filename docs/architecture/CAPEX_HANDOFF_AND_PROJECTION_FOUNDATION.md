# CAPEX Handoff And Projection Foundation

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner tasks: `TASK-0566`, `TASK-0567`
- Scope: internal CAPEX workflow/workpage foundation only.

This note records the first repo-native runtime contracts for CAPEX workflow handoff manifests, project-scoped workpage projection snapshots, signed projection cursors, and stale-command guards. It does not activate CAPEX workflows, expose public APIs, add frontend routes, import raw corpus material, or approve production/pilot readiness.

## Workflow Handoff Manifest
`capex.workflow_handoff_manifest.v1` is an internal contract object that binds downstream workflow handoff to exact basis truth:
- source workflow run scope
- artifact version IDs, kinds, and digests
- pointer IDs, pointer keys, and generations
- meaningful `source_occurrence:*` refs
- validation summaries
- closure evaluation and current closure snapshot refs
- task and workpage handoff bindings

Missing manifests, pointer generation drift, unresolved SourceRefs, stale/reopened closure snapshots, failed closure evaluations, missing validation summaries, and scope mismatches must block downstream handoff trust. The contract is not a replacement for canonical artifacts, audited pointers, or append-only events.

## Projection Snapshots And Commands
`capex_workpage_projection_snapshots` and `capex_workpage_projection_rows` are project-scoped read models for future CAPEX workpages. A snapshot records a deterministic `basis_hash` over its basis version vector and may be `current`, `stale`, or `superseded`.

Signed projection cursors bind snapshot ID, tenant/domain/project scope, basis hash, issue time, and expiry. Workpage command envelopes must carry the signed cursor and expected basis hash. Invalid signatures, expired cursors, scope mismatches, stale/superseded snapshots, and basis mismatch must reject before any mutation callback runs.

Workpage projections remain advisory read models. Commands must still mutate canonical runtime truth through existing command/event/artifact/pointer surfaces and shared command receipt idempotency.

## Rollback Posture
If handoff manifest validation or stale-command validation fails, block downstream workflow activation or CAPEX workpage command mutation. Do not destroy governed project, source occurrence, closure, artifact, pointer, projection snapshot, or command receipt state as a rollback mechanism.

## Remaining Blockers
The following remain later scope:
- authored CAPEX workflow packs and domain activation
- public CAPEX workpage read/write APIs
- frontend CAPEX workpage routes
- projection hydration families and performance batteries beyond the internal harness
- source occurrence relations, extraction, evidence binding, and raw-data governance
- CAPEX runtime/product activation
