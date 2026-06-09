---
id: TASK-0569
epic: EPIC-151
title: "Add interface-burden conservation policy and tests"
status: DONE
completed_at: 2026-06-09T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-151.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P1-009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Ensure interface responsibility is owned, transferred, waived, accepted residual, or open.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-151.md`
- `codex/context/EPIC-151.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: interface burden conservation tests
- Acceptance gate: `NU-GATE-009`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Interface burden policy; task spawn rules; residual risk acceptance path
- Review focus covered: No responsibility disappearance
- Refactor focus covered: Local policy helper
- Docs requirement covered: Update nuance addendum and workpage/task routing
- Rollback/recovery posture recorded: Block interface closure until policy passes

## Source row mapping
- Source task ID: `NU-CB-P1-009`
- Source phase: `P7 governance/interface`
- Source priority: `P1`
- Source area: `capex/interface`
- Original depends_on: `source occurrence; evidence binding`
- Source-only dependency notes: `source occurrence; evidence binding`
- Recommended source branch: `capex/interface-burden-policy`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `onetruth.capex_platform.interface_burden` as an internal policy helper for states `owned`, `transferred`, `waived`, `accepted_residual`, and `open`.
- The helper fails closed when responsibility lacks an owner, transfer target, waiver, residual-risk acceptance, or open follow-up owner, and requires traceable basis refs for non-open states.
- Open and transferred obligations return deterministic follow-up task specs as data only; this slice does not create runtime tasks or expose public workpage/API surfaces.
- Added `docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md` and contract coverage proving the policy, registration, and non-activation boundary.
- No CAPEX runtime/product activation, migrations, HTTP routes, frontend routes, raw corpus material, or second task system was introduced.
- Evidence: `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_capex_interface_burden_policy.py tests/contract/test_capex_interface_burden_policy_doc.py` passed on 2026-06-09.
