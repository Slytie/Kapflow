---
id: TASK-0262
epic: EPIC-140
title: "Implement project_membership and project roles"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0261"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Server-side user membership and role checks for project access.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-140.md`
- `codex/context/EPIC-140.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-140` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
project_membership; policy dependency; access checks

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: non-member denied; role capabilities; audit tests
- Acceptance gate: `AT-PROJ-002; AT-PROJ-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: project_membership; policy dependency; access checks
- Review focus covered: auth-before-read; no frontend-only filtering
- Refactor focus covered: centralize policy checks
- Docs requirement covered: access-control docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-002`
- Source phase: `P3 Project/access`
- Source priority: `P0`
- Source area: `auth/backend`
- Original depends_on: `PROJ-001`
- Converted repo dependencies: TASK-0261
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
