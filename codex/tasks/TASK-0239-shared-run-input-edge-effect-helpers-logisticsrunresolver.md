---
id: TASK-0239
epic: EPIC-137
title: "Shared run/input/edge effect helpers + LogisticsRunResolver"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR006` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Implement shared helpers for run/input/edge creation and stable logistics run resolution; detect activation-key drift.

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
- Source required tests: CR-005 plus regression tests
- Acceptance gate: `Run/input/edge helpers tested; activation drift test passes.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Run/input/edge helpers tested; activation drift test passes.
- Review focus covered: CR-005
- Refactor focus covered: RF-007
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR006`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR005`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
