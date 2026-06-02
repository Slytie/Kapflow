---
id: TASK-0258
epic: EPIC-139
title: "Create domain workpage/action descriptor registry"
status: TODO
owners: ["frontend"]
reviewers: ["platform", "qa"]
depends_on: ["TASK-0257"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `CLEAN-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Separate generic route contract from schedule/EOD/route/driver action dispatchers.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-139` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
domain registry; CAPEX descriptor extension point

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: projection and action dispatch tests
- Acceptance gate: `domain registry smoke tests`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: domain registry; CAPEX descriptor extension point
- Review focus covered: no logistics route assumptions in CAPEX
- Refactor focus covered: registry extraction; no hidden UI truth
- Docs requirement covered: workpage development guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `CLEAN-002`
- Source phase: `P2 Domain boundary`
- Source priority: `P0`
- Source area: `frontend/backend domain boundary`
- Original depends_on: `CLEAN-001`
- Converted repo dependencies: TASK-0257
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
