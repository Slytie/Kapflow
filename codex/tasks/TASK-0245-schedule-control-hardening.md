---
id: TASK-0245
epic: EPIC-139
title: "Schedule-control hardening"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238", "TASK-0240"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR012` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Stage04 outputs file-backed, evented, provenance-linked, receipt-scoped using generated helper; include weekly publish packet storage if feasible.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-007 plus regression tests
- Acceptance gate: `Six Stage04 outputs have created events, file URIs, provenance, receipt.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Six Stage04 outputs have created events, file URIs, provenance, receipt.
- Review focus covered: CR-007
- Refactor focus covered: RF-008
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR012`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR005;PR007`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- `schedule-control.build-weekly` is receipt-scoped through the shared command-boundary receipt path using workflow-run command scope.
- Weekly Stage04 output persistence now writes all six generated outputs through `persist_generated_artifact_effects`, producing root-confined file URIs, byte sizes, content digests, and canonical `artifact.version.created` events.
- Stage04 outputs retain explicit provenance from source input artifacts, and non-bundle outputs retain bundle-lowering provenance from the generated input bundle.
- Focused verification passed on 2026-06-02: `tests/runtime/test_schedule_control_hardening.py` and `tests/runtime/test_transaction_composition_safety.py`.
