---
id: TASK-0395
epic: EPIC-141
title: "Add manifest_generation attestation model for generated corpus registers"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0391", "TASK-0392"]
risk: medium
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W2-S05` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Generated register from physical rows only

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: red/characterization test or executable acceptance evidence before implementation
- Acceptance gate: `W2-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W2-S05; source wave W2; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W2
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W2-S05`
- Source phase: `P4/P5 Corpus and effects`
- Source priority: `P1`
- Source area: `corpus/effects/artifacts/validation`
- Original depends_on: `W2-S01/S02`
- Source-only dependency notes: `W2-S01/S02`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence: added `docs/planning/capex_source_ingest/MANIFEST_GENERATION_ATTESTATION_CONTRACT.yaml` and `src/onetruth/capex_platform/manifest_generation_attestation.py` for deterministic `capex.generated_corpus_register_manifest.v1`, `capex.manifest_generation_attestation.v1`, and wrapper `capex.manifest_generation_attestation.outputs.v1` planning outputs from physical corpus rows only.
- The helper validates same tenant/domain/project, tenant/domain content identity scope, canonical SourceRefs, known relation membership, input digests, generator config digest, duplicate IDs, deterministic row/register/basis digests, and the rule that generated corpus registers are evidence only, not source authority.
- Evidence: focused manifest-generation attestation unit tests and CAPEX ingest/generated-artifact contract tests cover deterministic output, physical-row basis, unknown refs, scope mismatch, duplicate IDs, bad digests, raw-content bans, and no runtime/official truth effects.
- Closeout posture: this task records generated-register attestation evidence only. It adds no duplicate migration, raw corpus import, parser/archive extraction runtime, locator union, route, frontend, event-registry change, reviewed baseline truth, official pointer, workflow activation, or CAPEX product/runtime activation.
