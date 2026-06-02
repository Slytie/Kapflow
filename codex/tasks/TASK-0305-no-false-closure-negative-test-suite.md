---
id: TASK-0305
epic: EPIC-149
title: "No-false-closure negative test suite"
status: TODO
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: ["TASK-0278", "TASK-0287"]
risk: high
context_packs:
  - "codex/context/EPIC-149.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `TEST-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Settlement-not-RCA, handover-not-closure, latest-not-official, empty-source-ref, stale-pointer.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-149.md`
- `codex/context/EPIC-149.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-149` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
negative test suite

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: guardrail tests fail on anti-patterns
- Acceptance gate: `NU-015`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: negative test suite
- Review focus covered: negative tests are product value
- Refactor focus covered: fixtures minimized
- Docs requirement covered: guardrail docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `TEST-002`
- Source phase: `P9 Validation`
- Source priority: `P0`
- Source area: `testing`
- Original depends_on: `ART-003; WFLOW-005`
- Converted repo dependencies: TASK-0278, TASK-0287
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
