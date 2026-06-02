---
id: TASK-0236
epic: EPIC-137
title: "Transaction composition safety"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0234"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Replace local BEGIN helpers in schedule_control/logistics_handoff receipt paths; expose/use savepoint-aware public transaction boundary.

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

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-002 plus regression tests
- Acceptance gate: `Handlers can run inside existing transaction; no nested transaction failures.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Handlers can run inside existing transaction; no nested transaction failures.
- Review focus covered: CR-002
- Refactor focus covered: RF-004
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR003`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR001`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- `command_transaction(connection)` is now a public shared command-boundary helper and uses a savepoint when the caller already owns an open transaction.
- Schedule-control output persistence and logistics handoff command handlers use the shared helper instead of local `BEGIN`/`BEGIN IMMEDIATE` helpers or manual commit/rollback blocks.
- Transaction composition regressions prove the schedule-control and logistics-handoff paths can run inside an existing transaction and that an outer rollback still rolls back their effects.
- Focused transaction regressions passed on 2026-06-02 with `python3.11 -m pytest -q tests/runtime/test_transaction_composition_safety.py`.
- This closes `MP-PR003` as a repo runtime safety gate only; it does not activate CAPEX production or change schema/API contracts.
