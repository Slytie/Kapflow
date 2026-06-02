---
id: TASK-0581
epic: EPIC-143
title: "Define workflow handoff manifest"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `V5-TASK-010` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Bind version, pointer generation, validation, stale basis, open issue status

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-143.md`
- `codex/context/EPIC-143.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: none specified in v6 source row
- Acceptance gate: `V5-GATE-010`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: V5-GATE-010
- Review focus covered: normal code/document review
- Refactor focus covered: none specified
- Docs requirement covered: none specified
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `V5-TASK-010`
- Source phase: `not specified`
- Source priority: `P1`
- Source area: `runtime/catalog`
- Original depends_on: `none`
- Recommended source branch: `not specified`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
