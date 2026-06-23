---
id: TASK-0276
epic: EPIC-142
title: "Implement generated artifact envelope and canonical naming"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238"]
risk: high
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ART-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Every capex.* artifact uses canonical envelope, kind, schema_version, source_refs, input digests, validation summary.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-142.md`
- `codex/context/EPIC-142.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: canonical name tests; deprecated name rejection
- Acceptance gate: `IMP-004; V-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: generated artifact helper integration; schema registry
- Review focus covered: no second truth; deterministic bytes
- Refactor focus covered: common helper; remove duplicates
- Docs requirement covered: generated artifact guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `ART-001`
- Source phase: `P6 Generated artifacts`
- Source priority: `P0`
- Source area: `schemas/backend`
- Original depends_on: `PR005`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `schemas/runtime/capex_generated_artifact_envelope.schema.json` for the CAPEX generated artifact envelope shape: `schema_version`, canonical `artifact_kind`, `artifact_role`, `source_refs`, `input_digests`, `validation_summary`, and `payload`.
- Added `docs/planning/capex_generated_artifacts/GENERATED_ARTIFACT_ENVELOPE_CONTRACT.yaml` as the repo-native `ART-001` contract and explicit unblocker for `TASK-0283`.
- Extended the shared generated-artifact helper with CAPEX envelope builders, canonical `capex.<family>.<artifact>.vN.json` naming, deprecated-name rejection, and a CAPEX wrapper that delegates persistence to `persist_generated_artifact_effects(...)`.
- Focused tests cover schema validation, deterministic canonical bytes, canonical persistence/name/digest behavior, deprecated-name rejection, invalid envelope shape rejection, and unchanged non-CAPEX generated-artifact helper behavior.
- Closeout posture: this closes the envelope and canonical-naming prerequisite only. Bundle validators, meaningful SourceRef/evidence sufficiency policy, pointer-promotion policy, workflow pack activation, public routes, raw corpus import, official pointer creation, and CAPEX runtime/product activation remain later gated work.
