---
id: TASK-0333
epic: EPIC-149
title: "P2 phase preflight quality review"
status: TODO
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-149.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `QD-P2-A` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Before Domain boundary and logistics side-effect extraction, confirm gates, test gaps, reviewers, and refactor candidates.

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
phase preflight note

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: As required by quality gates: QG-00;QG-01;QG-02
- Acceptance gate: `QG-00;QG-01;QG-02`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: phase preflight note
- Review focus covered: phase lead + primary reviewers; gates=QG-00;QG-01;QG-02
- Refactor focus covered: Use conservative refactor policy; separate pure refactor unless local/tiny/justified.
- Docs requirement covered: Update docs/templates/registers as applicable; see QUALITY_OVERLAY.
- Rollback/recovery posture recorded: Required for Tier 3+ or phase closeout; otherwise document not applicable.

## Source row mapping
- Source task ID: `QD-P2-A`
- Source phase: `P2`
- Source priority: `P0`
- Source area: `phase quality`
- Original depends_on: `prior phase closeout`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: prior phase closeout
- Recommended source branch: `analysis/capex-planning or feature branch`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
