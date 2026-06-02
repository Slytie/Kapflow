---
id: TASK-0256
epic: EPIC-138
title: "Pilot deployment gate"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0234", "TASK-0235", "TASK-0236", "TASK-0237", "TASK-0238", "TASK-0239", "TASK-0240", "TASK-0241", "TASK-0242", "TASK-0243", "TASK-0244", "TASK-0245", "TASK-0246", "TASK-0247", "TASK-0248", "TASK-0249", "TASK-0250", "TASK-0251", "TASK-0252", "TASK-0253", "TASK-0254", "TASK-0255"]
risk: high
context_packs:
  - "codex/context/EPIC-138.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR023` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Manual pilot deploy by image digest with predeploy backup, postdeploy smoke, invariant audit, login smoke, rollback plan.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-138` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Pilot gate checklist all green; manual approval recorded.

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-012 plus regression tests
- Acceptance gate: `Pilot gate checklist all green; manual approval recorded.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Pilot gate checklist all green; manual approval recorded.
- Review focus covered: CR-012
- Refactor focus covered: none specified
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR023`
- Source phase: `P10 Deployment/Logistics readiness`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR001-PR021;PR022 optional if apply required`
- Converted repo dependencies: TASK-0234, TASK-0235, TASK-0236, TASK-0237, TASK-0238, TASK-0239, TASK-0240, TASK-0241, TASK-0242, TASK-0243, TASK-0244, TASK-0245, TASK-0246, TASK-0247, TASK-0248, TASK-0249, TASK-0250, TASK-0251, TASK-0252, TASK-0253, TASK-0254, TASK-0255
- Source dependency notes still to satisfy: optional if apply required
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
