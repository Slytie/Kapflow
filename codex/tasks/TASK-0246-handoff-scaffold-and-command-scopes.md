---
id: TASK-0246
epic: EPIC-139
title: "Handoff scaffold and command scopes"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0239", "TASK-0240"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR013` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add handoff effect scaffold, command scopes, no behavior-complete claims; prepare weekly seed/live/notify paths.

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
Command scopes include source truth/target partition/policy version; scaffold tests pass.

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-008 plus regression tests
- Acceptance gate: `Command scopes include source truth/target partition/policy version; scaffold tests pass.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Command scopes include source truth/target partition/policy version; scaffold tests pass.
- Review focus covered: CR-008
- Refactor focus covered: RF-009
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR013`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR006;PR007`
- Converted repo dependencies: TASK-0239, TASK-0240
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
