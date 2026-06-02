---
id: TASK-0323
epic: EPIC-138
title: "Run full deployment and branch collision review when roadmap is supplied"
status: TODO
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0241", "TASK-0242", "TASK-0243", "TASK-0244", "TASK-0245", "TASK-0246", "TASK-0247", "TASK-0248", "TASK-0249", "TASK-0250", "TASK-0251", "TASK-0252", "TASK-0253", "TASK-0254", "TASK-0255", "TASK-0256"]
risk: high
context_packs:
  - "codex/context/EPIC-138.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SAFE-C-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Assess production/deployment roadmap, branch protection, storage/auth/migration changes, and exact CAPEX runtime branch point.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-138.md`
- `codex/context/EPIC-138.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: Branch point decision references active production/deployment plan and collision matrix.
- Acceptance gate: `SPC-G001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Full Safety Pass C result; final branch point recommendation
- Review focus covered: no mixing of production hardening and CAPEX runtime work without explicit gates
- Refactor focus covered: separate production branch, docs branch, CAPEX integration branch
- Docs requirement covered: MASTER_Branch_Execution_Model.md; deployment docs
- Rollback/recovery posture recorded: defer runtime integration branch if collision is unresolved

## Source row mapping
- Source task ID: `SAFE-C-001`
- Source phase: `branch_deployment_safety`
- Source priority: `P0`
- Source area: `deployment/branching`
- Original depends_on: `deployment roadmap; branch policy; PR008-PR023 plan`
- Source-only dependency notes: `deployment roadmap; branch policy; plan`
- Recommended source branch: `analysis/capex-master-plan`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
