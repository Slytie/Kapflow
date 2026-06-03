> Document classification: normative logistics current-state source. See `docs/domains/logistics/DOC_INVENTORY.yaml`.

# LOGISTICS_FAMILY_DEFINITIONS_AND_COMPILATION.md

## Purpose
This note defines the first logistics tranche as a definitions-layer extension over the fixed Strategy A substrate seam.

Formal posture:

\[
\Omega_2 = (\Omega_1, \mathcal D, \mathcal C, \mathcal H)
\]

This task lands only \(\mathcal D\): authored family definitions and deterministic compilation surfaces.

## Why `StateRef` should be typed later, not a flat address tuple
The logistics family touches multiple state disciplines:
- registry-like current-state pointers (published weekly schedule, approved plan),
- ordered streams (live dispatch delta and intake),
- future relation/journal surfaces (cross-workflow handoff and reconciliation links).

One flat tuple blurs those laws and reopens identity migration risk right after Strategy A closure.
Typed references keep semantics explicit:
- `RegistryRef` for canonical pointer-addressed official state,
- `JournalRef` for append-only posting surfaces,
- `RelationRef` for explicit relation/valid-time edges.

For this slice, runtime backing remains `RegistryRef` only. Journal/relation variants stay definition-time placeholders.

## Why this prompt lands only the `D` layer
The tranche goal is monotone extension without substrate churn.
Landing \(\mathcal D\) first provides:
- canonical family/module/edge authored surfaces,
- typed transform declarations,
- deterministic compiled descriptors.

It intentionally does not add:
- handoff execution runtime state (\(\mathcal H\)),
- new activation runtime model (\(\mathcal C\) runtime behavior),
- connector execution or composition workers.

That keeps the first logistics slice small, auditable, and compatible with the existing one-truth runtime.

## Why compiler behavior is fail-closed
Cross-workflow semantics in logistics are high-risk when guessed (activation policy, idempotency mode, transform kind).
The compiler therefore rejects underspecified or ambiguous definitions:
- missing first-slice handoff control fields (for example `idempotency_mode`),
- unknown or non-deterministic transform references,
- transform kind mismatches against source/target module partition kinds,
- stage/dataset edge refs that do not bind to unique authoritative artifacts.

No implicit fallback paths are used for first-slice semantics.
If semantics are not explicit, compilation fails.

## First-slice defaults made explicit
The authored family defaults and compiled descriptors carry these values explicitly:
- `daily_seed_shape = one_logical_seed_per_service_date`
- `live_delta_semantics = ordered_stream`
- `connectors_mode = fixture_only`
- `partition_transform_policy = typed_registry_required`

This avoids hidden behavior and keeps replay/verification stable.

## Surfaces landed
- Authored logistics workflow packs:
  - `weekly_schedule_planning/v1`
  - `live_dispatch/v1`
  - `availability_request/v1`
  - `dispatch_reporting/v1`
  - `timecard_audit/v1`
- Family authored surfaces:
  - `docs/workflows/logistics_ops_family/v1/WORKFLOW_FAMILY.yaml`
  - `docs/workflows/logistics_ops_family/v1/PARTITION_TRANSFORMS.yaml`
- Schemas:
  - `schemas/workflows/workflow_family.schema.json`
  - `schemas/workflows/partition_transform_registry.schema.json`
  - `schemas/workflows/compiled_module_definition.schema.json`
  - `schemas/workflows/compiled_family_edge.schema.json`
  - `schemas/workflows/state_ref.schema.json`
- Compiler/service:
  - `src/onetruth/infrastructure/definitions/family_compiler.py`
  - `src/onetruth/domain/partition_codec.py`
- Examples:
  - `docs/examples/logistics_definitions/*`

## Out of scope (kept explicit)
- no runtime edge execution table or composition worker,
- no new activation object model,
- no real connector ingress path,
- no automatic availability/reporting/timecard runtime handoff in this slice.
