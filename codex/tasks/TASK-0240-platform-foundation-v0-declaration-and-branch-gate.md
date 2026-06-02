---
id: TASK-0240
epic: EPIC-137
title: "Platform Foundation v0 declaration and branch gate"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0234", "TASK-0235", "TASK-0236", "TASK-0237", "TASK-0238", "TASK-0239"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Declare PF0 only if PR001-006 pass; open engineering runtime only within allowed mutation scope.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-137.md`
- `codex/context/EPIC-137.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-137` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Branch gate matrix updated; engineering runtime constraints enforceable.

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-005 plus regression tests
- Acceptance gate: `Branch gate matrix updated; engineering runtime constraints enforceable.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Branch gate matrix updated; engineering runtime constraints enforceable.
- Review focus covered: CR-005
- Refactor focus covered: none specified
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR007`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR001-PR006`
- Converted repo dependencies: TASK-0234, TASK-0235, TASK-0236, TASK-0237, TASK-0238, TASK-0239
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
