---
id: TASK-0281
epic: EPIC-142
title: "Implement stale/reopen register and rules"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0278", "TASK-0287"]
risk: high
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ART-006` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Upstream changes create scoped stale/re-review tasks rather than silent mutation.

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

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: order revision stale tests; new evidence reopen tests
- Acceptance gate: `WF-008; AT-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: capex.stale_reopen_register.v1.json
- Review focus covered: no silent state mutation
- Refactor focus covered: rule registry
- Docs requirement covered: stale/reopen docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `ART-006`
- Source phase: `P9 Officialness`
- Source priority: `P0`
- Source area: `workflow/validation`
- Original depends_on: `ART-003; WFLOW-005`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
