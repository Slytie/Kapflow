# CAPEX Domain Runtime Manifests

## Purpose
CAPEX domain runtime manifests are a Wave 1 inventory surface for composing domain packs without importing domain code into the neutral CAPEX platform package.

`src/onetruth/capex_platform/domain_runtime/` owns the typed manifest loader, registry, and deterministic composition report. Domain-specific truth remains in the domain's existing workflow packs, workpage descriptor/action packs, hook registries, and architecture docs.

## Boundary
- Manifests describe domain inventory; they do not activate runtime behavior.
- `activation_allowed` is always `false` in the current composition report.
- `capex_platform` must not import logistics/domain modules or domain document trees.
- Raw project corpora and extracted corpus content are not valid manifest content.
- A ready manifest means the existing domain inventory can be characterized, not that CAPEX product/runtime behavior is enabled.

## Current Manifests
- `docs/domains/logistics/domain.yaml` inventories the existing logistics workflow family, active workpage descriptors/actions, approval-response hooks, and handoff edges in ready state.
- The future CAPEX domain manifest is still owned by later EPIC-140 work and remains incubation/not-ready until its governance gates close.

## Source Of Truth
- Workflow semantics remain in `docs/workflows/*/v1/`.
- Workpage descriptor and action behavior remains in the registered Python packs.
- Approval-response side effects remain behind registered hooks.
- Domain manifests are checked by `schemas/domain_runtime/domain_manifest.schema.json` and characterization tests.
