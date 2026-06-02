---
id: TASK-0568
epic: EPIC-149
title: "Add CAPEX semantic test suite and CODEOWNERS gates"
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
Imported from CAPEX v6 source task `NU-CB-P0-008` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add semantic test markers, required CAPEX review owners, and missing CAPEX tests from CB2 backlog.

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
pytest markers; CI job; CODEOWNERS semantic owners; test matrix

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: All CB2-T001..T014 tracked and green by phase
- Acceptance gate: `NU-GATE-008`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: pytest markers; CI job; CODEOWNERS semantic owners; test matrix
- Review focus covered: Review/test evidence for every semantic change
- Refactor focus covered: No broad CI rewrite; incremental gates
- Docs requirement covered: Update TDD and review docs
- Rollback/recovery posture recorded: CAPEX feature gates stay off until semantic gates green

## Source row mapping
- Source task ID: `NU-CB-P0-008`
- Source phase: `P0/P1 quality foundation`
- Source priority: `P0`
- Source area: `quality/ci/review`
- Original depends_on: `TDD strategy; codebase pass 2`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: TDD strategy; codebase pass 2
- Recommended source branch: `foundation/capex-semantic-tests`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
