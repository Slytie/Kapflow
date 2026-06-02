---
id: TASK-0584
epic: EPIC-136
title: "Add dependency register and risk-based milestone overlay"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0582"]
risk: high
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create explicit dependency register and risk milestones for stakeholder aligned, architecture proven, system viable, business increment, production ready.

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
MASTER_Dependency_Register.csv; Risk_Based_Milestone_Model.csv

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: dependencies have owner/needed-by/mitigation
- Acceptance gate: `SD-GATE-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: MASTER_Dependency_Register.csv; Risk_Based_Milestone_Model.csv
- Review focus covered: no hidden precedence constraints
- Refactor focus covered: none
- Docs requirement covered: delivery cadence doc
- Rollback/recovery posture recorded: revert register patch

## Source row mapping
- Source task ID: `SD-TASK-003`
- Source phase: `P0/P1 planning`
- Source priority: `P0`
- Source area: `delivery/dependencies`
- Original depends_on: `SD-TASK-001`
- Converted repo dependencies: TASK-0582
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
