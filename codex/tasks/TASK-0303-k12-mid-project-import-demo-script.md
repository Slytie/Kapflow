---
id: TASK-0303
epic: EPIC-145
title: "K12 mid-project import demo script"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0283", "TASK-0302"]
risk: high
context_packs:
  - "codex/context/EPIC-145.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `K12-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
First demo path uses mid-project import and external/internal officialness.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-145.md`
- `codex/context/EPIC-145.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-145` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
demo script; acceptance flow

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: end-to-end fixture test
- Acceptance gate: `NU-001; NU-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: demo script; acceptance flow
- Review focus covered: do not auto-officialize historical files
- Refactor focus covered: script cleanup
- Docs requirement covered: demo docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `K12-004`
- Source phase: `P4/P7 K12 fixture`
- Source priority: `P0`
- Source area: `demo/test`
- Original depends_on: `K12-003; WFLOW-001`
- Converted repo dependencies: TASK-0283, TASK-0302
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
