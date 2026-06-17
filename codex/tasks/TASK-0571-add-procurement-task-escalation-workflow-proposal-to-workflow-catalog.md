---
id: TASK-0571
epic: EPIC-143
title: "Add procurement/task escalation workflow proposal to workflow catalog"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
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
- Source-only dependency notes: `workpage/task routing decisions`
- Recommended source branch: `capex/workflow-routing-docs`

## Closeout evidence
- Added `docs/planning/capex_workflow_catalog/procurement_escalation_workflow_proposal.yaml` as a planning-only CAPEX workflow catalog proposal for procurement and CEO escalation task chains.
- Added semantic contract coverage proving the proposal is task/approval-chain based, evidence-bound, not editable workpage status, and cannot activate CAPEX runtime/product/public routes or sign off procurement thresholds.
- Updated the SME-RP acceptance register, CAPEX domain manifest, EPIC-143 docs, and CB2 semantic backlog so `NU-GATE-011` has repo-native planning evidence while authored workflow packs and `TASK-0659` threshold signoff remain blocked.
- No runtime code, migrations, routes, frontend routes, raw corpus import, authored workflow pack activation, or CAPEX activation was introduced.

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
