---
id: TASK-0265
epic: EPIC-140
title: "Project-scoped official pointer families"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238", "TASK-0261"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Pointers and snapshots scoped by project_id + pointer_family + generation.

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
pointer family policy; expected-generation validation

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: stale generation tests; approval-not-pointer test
- Acceptance gate: `AT-OFFICIAL-004; NU-006`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: pointer family policy; expected-generation validation
- Review focus covered: no latest/approved shortcut
- Refactor focus covered: reuse generic pointer model carefully
- Docs requirement covered: pointer promotion guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-005`
- Source phase: `P9 Officialness`
- Source priority: `P0`
- Source area: `backend/pointers`
- Original depends_on: `PROJ-001; PR005`
- Converted repo dependencies: TASK-0238, TASK-0261
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
