---
id: TASK-0251
epic: EPIC-139
title: "Weekly-to-weekly carry-forward"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0239", "TASK-0250"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR018` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Canonical W_k -> W_{k+1}; target run/task/inputs/provenance/EdgeExecution; workpage calls canonical command.

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

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-010 plus regression tests
- Acceptance gate: `Carry-forward creates target once; no Stage04 auto-run/approval.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Carry-forward creates target once; no Stage04 auto-run/approval.
- Review focus covered: CR-010
- Refactor focus covered: none specified
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR018`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR017;PR006`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added canonical weekly-to-weekly route-demand carry-forward behind the existing add-next-week workpage action.
- Carry-forward now creates or reuses the target weekly run once, ensures only the `weekly_input_intake` task, seeds/reuses the target `planning.route_slot_requirements.workbook`, attaches it to the intake task, binds it as `stage04.route_slot_requirements`, records explicit provenance, and writes a `weekly_to_weekly_carry_forward` EdgeExecution.
- Target run activation-key drift now fails closed for weekly run reuse instead of silently attaching carry-forward truth to a differently activated run.
- Workpage add-next-week calls the canonical carry-forward helper and preserves the public `created` response shape while adding carry-forward evidence.
- Evidence: focused add-next-week regression and full route-demand workpage API contract suite passed on 2026-06-02.
- Closeout posture: `MP-PR018` is closed as weekly-to-weekly input carry-forward only; this does not auto-run Stage04, complete intake, request approvals, activate CAPEX production, deploy, or authorize reconciler apply mode.
