---
id: TASK-0278
epic: EPIC-142
title: "Implement schema and bundle validators"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0276"]
risk: high
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ART-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Validate JSON Schema plus cross-reference bundle consistency.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-142.md`
- `codex/context/EPIC-142.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-142` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
schema validator; bundle validator

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: missing ref; stale input; empty ref tests
- Acceptance gate: `V-002; V-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: schema validator; bundle validator
- Review focus covered: schema-valid not promotable
- Refactor focus covered: validator layer extraction
- Docs requirement covered: validation policy docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `ART-003`
- Source phase: `P6 Validation`
- Source priority: `P0`
- Source area: `validation`
- Original depends_on: `ART-001`
- Converted repo dependencies: TASK-0276
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
