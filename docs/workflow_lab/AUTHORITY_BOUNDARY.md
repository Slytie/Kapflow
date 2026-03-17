# Workflow Lab Authority Boundary

Workflow Lab is allowed to evaluate kernel behavior. It is not allowed to become a second authority chain.

## Authoritative inputs Workflow Lab may read
- repo-authored workflow packs under `docs/workflows/*/v1/*`
- compiled control derived from those workflow packs
- canonical runtime rows, append-only events, immutable artifacts, and audited pointers
- release artifacts such as `release_source_bundle`, `bundle_manifest.json`, and `release_provenance.json`

These inputs remain authoritative because they come from the existing kernel and reviewed release path.

## What Workflow Lab outputs are
Workflow Lab outputs are evidence or derived material:
- reports
- freshness assessments
- compare packets
- candidate evaluation notes

These outputs may inform review, certification, and release. They do not define workflow semantics, promotion truth, or direct production state.

## Promotion boundary
The healthy relationship remains:

- `lab -> review/certification/release -> prod`

Workflow Lab must not mutate production runtime state directly.

## Anti-patterns
Do not let Workflow Lab become:
- a second semantics compiler
- a public product surface in Phase 0
- a direct lab-to-prod runtime mutation path
- a raw production DB cloning path
- a place that treats semantic/version changes as if they were merely execution variants

Phase 0 does not require a `src/onetruth/workflow_lab/` package.

Prod and lab must remain separate environments with separate DBs, artifact roots, and secrets. Tenant/domain separation inside one environment is not an acceptable substitute.
