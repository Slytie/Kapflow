---
id: TASK-0580
epic: EPIC-136
title: "Add vertical-slice ladder and dependency register"
status: DONE
source_lineage: v5_carried_forward
active_disposition: historical_alias
canonical_task_refs: ["TASK-0583", "TASK-0584"]
owners: ["architect"]
reviewers: ["platform", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `V5-TASK-009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Define VS-00..VS-05 plus dependency owners/needed-by/mitigation

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

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: none specified in v6 source row
- Acceptance gate: `V5-GATE-009`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: V5-GATE-009
- Review focus covered: normal code/document review
- Refactor focus covered: none specified
- Docs requirement covered: none specified
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `V5-TASK-009`
- Source phase: `not specified`
- Source priority: `P0`
- Source area: `delivery/docs`
- Original depends_on: `none`
- Recommended source branch: `not specified`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Reconciliation closeout evidence
- This source row is carried forward from v5 inside the CAPEX v6 package and is closed as a historical alias, not as independent active backlog.
- Canonical active work remains on `TASK-0583`, `TASK-0584`; this closeout does not mark those target tasks complete unless their own task files record completion.
- CAPEX v6 remains the active planning baseline; v5 and earlier packages remain superseded history.
