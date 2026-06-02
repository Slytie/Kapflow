---
id: TASK-0314
epic: EPIC-150
title: "Safety Pass B: deployment roadmap/branch collision review"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-150.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SAFE-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Finalize exact branch point relative to production work and PR008-PR023.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-150.md`
- `codex/context/EPIC-150.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: collision matrix review
- Acceptance gate: `before CAPEX runtime branch`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: branch decision addendum
- Review focus covered: no uncontrolled branch mixing
- Refactor focus covered: none
- Docs requirement covered: branch addendum
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `SAFE-002`
- Source phase: `Safety pass`
- Source priority: `P0`
- Source area: `planning/branching`
- Original depends_on: `user provides deployment roadmap/current branch policy`
- Source-only dependency notes: `user provides deployment roadmap/current branch policy`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
