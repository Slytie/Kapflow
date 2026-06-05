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
- `docs/domains/capex/domain.yaml` inventories CAPEX in incubation state with no runnable workflows, workpages, or side effects. Its disabled capabilities and readiness prerequisites point to the accepted project authorization CED/prototype and projection runtime state, accepted storage/blob custody CED and pilot checklist, plus later real pilot storage evidence or waiver, source governance, workflow catalog, workpage projection, and production-preflight tasks.

## Project Authorization
- `docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md` records the Wave 1 project authorization boundary.
- `AuthorizedProjectsQuery` is a backend-only query surface over rebuildable projection rows derived from direct `project_memberships`; it does not activate CAPEX workflows or replace direct membership as source authority.

## Storage Custody
- `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md` records the future storage/blob custody schema boundary.
- `docs/planning/checklists/CAPEX_PILOT_STORAGE_GATE.md` records the pilot storage gate checklist with default result `blocked_pending_evidence`.
- These records do not add migrations, routes, storage backend rollout, Postgres rollout, raw-corpus approval, pilot readiness, or CAPEX activation.

## Wave 1 Pattern And Closeout
- `docs/architecture/CAPEX_W1_CODE_PATTERN_REGISTER.md` records illustrative, non-production pattern snippets for domain runtime, project visibility, and storage custody seams.
- `docs/architecture/CAPEX_W1_CLOSEOUT_REVIEW.md` records the Wave 1 decision docket and keeps the real pilot storage gate at `blocked_pending_evidence`.
- These records are closeout evidence only; they do not make manifests, storage custody, CAPEX workflows, or CAPEX runtime activation runnable.

## Approval Side Effects
- Approval-response side effects are selected through the neutral approval-effect registry in shadow mode.
- Logistics keeps its compatibility selector, but that selector delegates to the logistics approval-effect pack.
- The registry is parity evidence only in the current slice; it does not add CAPEX approval side effects or activation behavior.

## Source Of Truth
- Workflow semantics remain in `docs/workflows/*/v1/`.
- Workpage descriptor and action behavior remains in the registered Python packs.
- Approval-response side effects remain behind registered hooks.
- Domain manifests are checked by `schemas/domain_runtime/domain_manifest.schema.json` and characterization tests.
