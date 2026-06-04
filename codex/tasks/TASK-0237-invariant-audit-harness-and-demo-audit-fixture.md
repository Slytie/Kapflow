---
id: TASK-0237
epic: EPIC-137
title: "Invariant audit harness and demo audit fixture"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0235", "TASK-0236"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add invariant registry with gate_mode states; add fresh demo audit; hard-gate only resolved safety invariants, report known gaps.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-137.md`
- `codex/context/EPIC-137.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-003 plus regression tests
- Acceptance gate: `Audit report generated; known gaps tracked; no accidental permanent-red CI.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Audit report generated; known gaps tracked; no accidental permanent-red CI.
- Review focus covered: CR-003
- Refactor focus covered: RF-005
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR004`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR002;PR003`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added a CAPEX invariant audit registry with `hard_gate`, `known_gap`, and `advisory` gate modes.
- Initial hard gates cover PR001/PR002/PR003 repo safety posture: no active tracked `node_modules`, secretless/non-deploy Cloud Build PR validation, artifact root confinement/auth-before-read, and savepoint transaction composition.
- Known gaps are reported without failing CI for approval side-effect coupling, CAPEX project child APIs and authorization projections, source occurrence/SourceRef, and broader generated-artifact migration.
- Added `scripts/run_capex_invariant_audit.py`; direct run on 2026-06-02 passed with 4 hard gates green and 4 known gaps recorded.
- Focused audit tests passed with `python3.11 -m pytest -q tests/contract/test_capex_invariant_audit.py tests/unit/test_generated_artifact_helper.py`.
- This closes `MP-PR004` as a repo platform-readiness gate only; it does not activate CAPEX production.
