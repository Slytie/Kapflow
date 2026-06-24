---
id: TASK-0405
epic: EPIC-141
title: "Define SubmittedGeneratedArtifact and RuntimeGeneratedArtifactView schemas"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0401"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W2-S15` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Submitted artifact forbids runtime-owned fields

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
- Source output satisfied: Implementation artifact(s) implied by W2-S15; source wave W2; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W2
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W2-S15`
- Source phase: `P4/P5 Corpus and effects`
- Source priority: `P0`
- Source area: `corpus/effects/artifacts/validation`
- Original depends_on: `W2-S11`
- Source-only dependency notes: `W2-S11`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence adds `docs/planning/capex_generated_artifacts/SUBMITTED_RUNTIME_GENERATED_ARTIFACT_CONTRACT.yaml`, `schemas/runtime/capex_submitted_generated_artifact.schema.json`, `schemas/runtime/capex_runtime_generated_artifact_view.schema.json`, and `onetruth.capex_platform.generated_artifact_submission`.
- Submitted generated artifacts carry only author-supplied artifact kind/role, SourceRefs, input digests, validation summary, and payload; runtime-owned fields including artifact IDs, storage refs, digests, identity fields, pointer fields, officialness/status fields, event IDs, and timestamps are rejected.
- Runtime generated artifact views expose persisted artifact metadata with explicit non-authoritative posture. This task does not persist submissions, promote pointers, claim evidence sufficiency, create reviewed baselines, add public/frontend routes, import raw corpus data, or activate CAPEX runtime/product behavior.
