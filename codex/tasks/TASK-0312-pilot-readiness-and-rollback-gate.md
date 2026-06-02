---
id: TASK-0312
epic: EPIC-138
title: "Pilot readiness and rollback gate"
status: TODO
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0256", "TASK-0311"]
risk: high
context_packs:
  - "codex/context/EPIC-138.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `DEPLOY-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Run pilot gates, backup/restore, auth, rollback and manual approval plan.

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
pilot readiness gate; rollback plan

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: pilot smoke and restore proof
- Acceptance gate: `PG-01..PG-12`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: pilot readiness gate; rollback plan
- Review focus covered: no production secrets in PR
- Refactor focus covered: deployment scripts cleanup
- Docs requirement covered: runbook
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `DEPLOY-002`
- Source phase: `P10 Deployment`
- Source priority: `P0`
- Source area: `ops`
- Original depends_on: `PR023; DEPLOY-001`
- Converted repo dependencies: TASK-0256, TASK-0311
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
