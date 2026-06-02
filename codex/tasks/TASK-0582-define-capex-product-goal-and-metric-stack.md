---
id: TASK-0582
epic: EPIC-136
title: "Define CAPEX Product Goal and metric stack"
status: TODO
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create one-page Product Goal plus outcome, learning, flow, quality, and operability metrics.

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
- Source required tests: document lint; stakeholder signoff check
- Acceptance gate: `SD-GATE-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: MASTER_Product_Goal_and_Metrics.md; Product_Goal_Metric_Stack.csv
- Review focus covered: clarity, measurability, non-velocity bias
- Refactor focus covered: none
- Docs requirement covered: new master doc
- Rollback/recovery posture recorded: revert doc/register patch

## Source row mapping
- Source task ID: `SD-TASK-001`
- Source phase: `P0 Source freeze`
- Source priority: `P0`
- Source area: `delivery/product-governance`
- Original depends_on: `none`
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
