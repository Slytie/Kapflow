> Document classification: normative logistics current-state source. See `docs/domains/logistics/DOC_INVENTORY.yaml`.

# LOGISTICS_CONTROL_LAYER_AND_METHOD_PACKAGES.md

## Purpose
This note defines the first logistics control-layer (`C`) slice over the fixed Strategy A substrate and the previously-landed logistics definitions (`D`) slice.

Formal posture:

\[
\Omega_2 = (\Omega_1, \mathcal D, \mathcal C, \mathcal H)
\]

This task lands only a compiled control metadata layer (`\mathcal C`) and method-package pinning surfaces.

## Canonical runtime object law (unchanged)
Existing runtime objects remain canonical:
- `workflow_runs`
- `task_runs`
- `human_tasks`
- `execution_sessions`
- `tool_executions`

Control metadata in this slice only *drives* those existing objects.
It does not introduce a second activation ontology and does not add new top-level activation tables.

## Control-layer scope in this slice
The slice adds:
- authored logistics method-package registry (`METHOD_PACKAGES.yaml`),
- deterministic compiled stage execution specs,
- activation request schema/validation from compiled definitions,
- execution-session payload derivation from compiled control metadata.

The slice explicitly does not add:
- handoff execution runtime,
- connector execution,
- alternate activation state engines,
- LLM-first ranking semantics.

## Method-package pinning requirements
Method packages pin enough behavior metadata for deterministic replay/review:
- stage applicability (`workflow_id`, `stage_id`, execution pattern),
- context/tool/output/lowering references,
- stop policy,
- replay policy and deterministic fields,
- content digest (`sha256`) and derived execution-spec identity.

Behavior-package changes therefore produce new pin digests and new execution-spec IDs.

## Determinism and fail-closed behavior
Compilation fails closed when required first-slice control metadata is missing or inconsistent:
- missing method package for a required first-slice stage,
- duplicate method-package stage bindings,
- execution-pattern mismatch between stage definition and method package,
- malformed activation request pointer/scope/partition bindings,
- missing required activation input dataset bindings.

No implicit fallback control behavior is allowed.

## Bounded stochastic assistance
For first-slice logistics control semantics:
- deterministic candidate filtering/ranking remains primary,
- optional LLM rationale is allowed only as bounded non-authoritative support,
- stochastic output must not reorder deterministic ranking or bypass canonical approvals/promotion rules.

## Why this is ready for handoff runtime follow-on
This slice establishes deterministic compiled control metadata and pinning needed to safely proceed to explicit handoff runtime work (`\mathcal H`) in a later task, while preserving one canonical runtime truth system.
