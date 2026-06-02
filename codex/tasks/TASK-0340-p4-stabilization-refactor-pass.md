---
id: TASK-0340
epic: EPIC-149
title: "P4 stabilization/refactor pass"
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
Imported from CAPEX v6 source task `QD-P4-B` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Run behavior-preserving cleanup after Real-project fixture governance and sanitized K12 fixture implementation; retire scaffolds or create debt records.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-149` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
refactor PRs/debt register

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: As required by quality gates: QG-06;QG-12
- Acceptance gate: `QG-06;QG-12`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: refactor PRs/debt register
- Review focus covered: primary + relevant specialist; gates=QG-06;QG-12
- Refactor focus covered: Use conservative refactor policy; separate pure refactor unless local/tiny/justified.
- Docs requirement covered: Update docs/templates/registers as applicable; see QUALITY_OVERLAY.
- Rollback/recovery posture recorded: Required for Tier 3+ or phase closeout; otherwise document not applicable.

## Source row mapping
- Source task ID: `QD-P4-B`
- Source phase: `P4`
- Source priority: `P1`
- Source area: `refactoring`
- Original depends_on: `P4 implementation slices`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: P4 implementation slices
- Recommended source branch: `feature/capex-p4-stabilize`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
