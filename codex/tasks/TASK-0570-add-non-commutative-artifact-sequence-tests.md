---
id: TASK-0570
epic: EPIC-142
title: "Add non-commutative artifact sequence tests"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P1-010` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Demonstrate different artifact order produces different stale/closure/commitment outcomes.

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
- Source required tests: non-commutative transition tests
- Acceptance gate: `NU-GATE-010`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Sequence fixture cases; operator evaluation tests
- Review focus covered: Event order and pointer generation are reviewed
- Refactor focus covered: Test-only initially
- Docs requirement covered: Update formalism guardrails
- Rollback/recovery posture recorded: No runtime change

## Source row mapping
- Source task ID: `NU-CB-P1-010`
- Source phase: `P6/P7 artifact-state`
- Source priority: `P1`
- Source area: `capex/formalism/tests`
- Original depends_on: `artifact/operator model; event ordering`
- Source-only dependency notes: `artifact/operator model; event ordering`
- Recommended source branch: `capex/formalism-sequence-tests`

## Closeout evidence
- Added closure sequence coverage proving a basis-change recurrence before snapshot creation leaves a later snapshot current, while the same basis-change recurrence after snapshot creation marks the existing snapshot stale.
- Added official pointer sequence coverage proving promotion order changes final project official pointer target and generation history.
- Updated `docs/architecture/CAPEX_SOURCE_REF_AND_CLOSURE_GUARDRAILS.md` to record that CAPEX artifact, pointer, and closure transitions are non-commutative and later evidence does not retroactively rewrite earlier governed outcomes.
- No runtime code, migrations, routes, frontend routes, raw corpus import, or CAPEX activation was introduced.

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
