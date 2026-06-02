---
id: TASK-0330
epic: EPIC-149
title: "Add architecture boundary forbidden-pattern checks"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-149.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `QD-006` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Advisory Semgrep/grep checks for raw-data leakage, logistics leakage into CAPEX, direct pointer mutation.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-149.md`
- `codex/context/EPIC-149.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: As required by quality gates: QG-03;QG-09
- Acceptance gate: `QG-03;QG-09`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: docs/templates/register update
- Review focus covered: primary + docs/process owner; gates=QG-03;QG-09
- Refactor focus covered: Use conservative refactor policy; separate pure refactor unless local/tiny/justified.
- Docs requirement covered: Update docs/templates/registers as applicable; see QUALITY_OVERLAY.
- Rollback/recovery posture recorded: Required for Tier 3+ or phase closeout; otherwise document not applicable.

## Source row mapping
- Source task ID: `QD-006`
- Source phase: `P1`
- Source priority: `P1`
- Source area: `tooling`
- Original depends_on: `current master plan`
- Source-only dependency notes: `current master plan`
- Recommended source branch: `analysis/capex-planning`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
