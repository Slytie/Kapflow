---
id: TASK-0579
epic: EPIC-136
title: "Add Product Goal and metric stack"
status: TODO
owners: ["architect"]
reviewers: ["platform", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `V5-TASK-008` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create one-page goal and metrics with signoff

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-136.md`
- `codex/context/EPIC-136.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-136` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Record any generated or downstream artifacts in the task implementation notes.

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: none specified in v6 source row
- Acceptance gate: `V5-GATE-008`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: V5-GATE-008
- Review focus covered: normal code/document review
- Refactor focus covered: none specified
- Docs requirement covered: none specified
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `V5-TASK-008`
- Source phase: `not specified`
- Source priority: `P0`
- Source area: `delivery/docs`
- Original depends_on: `none`
- Converted repo dependencies: none
- Recommended source branch: `not specified`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
