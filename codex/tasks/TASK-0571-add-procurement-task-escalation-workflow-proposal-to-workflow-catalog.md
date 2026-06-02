---
id: TASK-0571
epic: EPIC-143
title: "Add procurement/task escalation workflow proposal to workflow catalog"
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
Imported from CAPEX v6 source task `NU-CB-P1-011` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Represent procurement/work/component decision flows as task chains with CEO escalation, not editable table-only workpages.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-143` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Workflow/task catalog rows; escalation gate definitions

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: procurement escalation tests
- Acceptance gate: `NU-GATE-011`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Workflow/task catalog rows; escalation gate definitions
- Review focus covered: Task vs workpage boundaries clear
- Refactor focus covered: Catalog/documentation only until runtime implemented
- Docs requirement covered: Update SME signoff and workflow docs
- Rollback/recovery posture recorded: No runtime change

## Source row mapping
- Source task ID: `NU-CB-P1-011`
- Source phase: `P8/P9 workflow/product`
- Source priority: `P1`
- Source area: `capex/workflow/tasks`
- Original depends_on: `workpage/task routing decisions`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: workpage/task routing decisions
- Recommended source branch: `capex/workflow-routing-docs`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
