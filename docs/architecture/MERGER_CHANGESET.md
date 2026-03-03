# Merger changeset

This document records the detailed repo changes applied to merge the Stage 4 scaffold with the CompanyOS packet without creating a second truth system.

## 1) Structural changes applied

### Added
- `docs/vision/` curated philosophy, mathematics, source lineage, threat-model guidance
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/EXECUTION_OVERLAY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/architecture/MERGER_CHANGESET.md`
- `docs/architecture/DOCUMENT_STATUS_MATRIX.md`
- `docs/architecture/LOWERING_CONTRACT.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/workflows/*/v1/DECISION_CATALOG.yaml`
- `docs/workflows/*/v1/EXECUTION_PROFILE.yaml`
- `docs/templates/` for future workflow packs
- `schemas/agentic/` for decision catalog and execution profile
- `schemas/events/event_type_registry.yaml`
- `schemas/artifacts/artifact_version_metadata.schema.json`
- `docs/planning/MERGER_BACKLOG.md`
- new epics and tasks for the one-truth merger

### Updated
- repo read path (`README`, `AGENTS`, `CODEX_CONTEXT`, docs index)
- planning docs and current focus
- workflow README files
- placeholder architecture docs, ops docs, security doc
- signoff checklists
- event envelope descriptions

### Explicitly not imported as peer source
- authored CompanyOS `WorkflowSpec`
- authored `ProcessPatch`
- spike-repo `agent_runs` and `human_decision_requests` as a separate parallel truth model

## 2) Key design decision
The repo now treats the CompanyOS packet as:
- philosophy
- math
- threat model
- lowering target

not as a second authored workflow-definition system.

## 3) Canonical authored workflow surface
Per workflow, the hand-authored source surface is now:

- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `ACCEPTANCE_CRITERIA.md`
- `OPERATING_MODEL.md`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`

Everything else is downstream.

## 4) Stale-material cleanup
The main stale risks before this changeset were:
- Schedule Planning tasks marked TODO even though the pack already existed
- placeholder architecture docs with no runtime guidance
- no repo-native place preserving CompanyOS philosophy and mathematics
- no explicit authority chain
- no file in the repo saying generated runbook packs must not become source

These are now addressed.

## 5) Deferred with nuance preserved
See `docs/planning/MERGER_BACKLOG.md` for deferred items that should not be forgotten:
- generated CompanyOS IR pipeline
- ProcessPatch lifecycle
- spec store
- WorkGraph
- projection DSLs
- multi-level workflows
- capability diff tooling
- cross-tenant learning

## 6) Extra control documents added for maintainability
- `DOCUMENT_STATUS_MATRIX.md` prevents stale or ambiguous docs by marking authoritative vs generated vs historical materials.
- `LOWERING_CONTRACT.md` makes the CompanyOS merge precise: repo-native source lowers into generated IR and compiled `ExecutionSpec`.
- `RUNTIME_OBJECT_MODEL.md` prevents the spike runtime from reappearing as a second implicit truth model.
