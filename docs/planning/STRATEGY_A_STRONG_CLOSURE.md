# STRATEGY_A_STRONG_CLOSURE.md

Design note for TASK-0059.

## 1) Closure target
Strategy A is strongly closed only when canonical pointer identity is authoritative end-to-end for:
- authoritative promotion writes,
- authoritative promotion/drift events,
- public pointer query surfaces,
- demo-facing official-output reads.

The closure law for safe follow-on work is monotone extension:

\[
\Omega_{1+\Delta} = E(\Omega_1)
\]

where new layers `E` add behavior without reinterpreting historical officialness.

## 2) Canonical identity vs legacy carriers

### Canonical pointer identity (authoritative)
- `artifact_pointers.pointer_id` is canonical pointer-stream identity.
- Canonical address fields (`tenant_id`, `domain_id`, `dataset_key`, `partition_kind`, `partition_key`, `stream_key`, `registry_kind`) define pointer scope and query semantics.
- Promotion CAS semantics (`generation`, `expected_generation`) are evaluated on canonical stream identity.

### Legacy carriers (compatibility-only)
- `workflow_run_id`
- `pointer_key`

These are retained so run-centric reads and older callers still work, but they do not define officialness ownership.

## 3) Authoritative behavior after strong closure

### Writes
- Promotions fail closed if canonical identity cannot be safely resolved.
- Promotion scope checks remain canonical and scope-strict.
- Compatibility alias fields are updated as adapters only.

### Events
- `artifact.pointer.promoted.payload.pointer_id` is canonical pointer identity.
- `artifact.pointer.drift_detected.payload.pointer_id` is canonical pointer identity.
- Pointer event `dataset_key` comes from canonical pointer identity semantics (not caller casing artifacts).

### Public reads
- `/api/v1/pointers` supports canonical-first querying (`pointer_id`, canonical address filters) without requiring run-local keys.
- `workflow_run_id` filtering remains as compatibility alias behavior.

### Demo/workspace/export surfaces
- Official-output projections resolve pointer targets via canonical scoped artifact identity.
- Same-scope cross-run pointer targets remain resolvable without creating a second truth path.

## 4) Why the next tranche is monotone now
- Historical pointer streams are identified canonically.
- Event evidence references canonical pointer identity directly.
- Public reads can query canonical identity/address directly.
- Compatibility carriers are adapters over the same canonical rows/events.

Therefore follow-on features can compose on top of the post-closure substrate without reinterpreting prior officialness.

## 5) Physical PK replacement posture
A physical PK replacement was already completed in migration `20260307_0008_pointer_identity_strong_closure.py`.
This closure pass did not require another structural re-key. Remaining legacy fields are intentionally retained as compatibility carriers.

## 6) Residual compatibility debt (safe)
- CLI read commands remain run-key oriented (`pointers show/list`) for operator ergonomics.
- Run-centric filters remain available on `/api/v1/pointers` as compatibility aliases.

This debt is safe because canonical write/event/public-read semantics no longer depend on legacy carriers.
