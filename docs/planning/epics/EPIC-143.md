# EPIC-143 - CAPEX workflow catalog

## Summary
Define CAPEX workflow slices for intake, baseline, lifecycle, commitments, assumptions, interfaces, snapshots, and risk.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0566` is closed as of 2026-06-08 with an internal handoff manifest schema and validation guard; authored CAPEX workflow packs and runtime activation remain open.

## In scope
- Source task families/counts: NU:2, V5:2, WFLOW:7.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-140, EPIC-142

Context pack:
- `codex/context/EPIC-143.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0283` (`WFLOW-001`) - Project Intake Router workflow
- `TASK-0284` (`WFLOW-002`) - Corpus Baseline workflow
- `TASK-0285` (`WFLOW-003`) - Lifecycle Stage State workflow
- `TASK-0286` (`WFLOW-004`) - Governance / Commitment Chain workflow
- `TASK-0287` (`WFLOW-005`) - Assumption Closure workflow
- `TASK-0288` (`WFLOW-006`) - Owner Interface Resolution workflow
- `TASK-0289` (`WFLOW-007`) - Project State Snapshot workflow
- `TASK-0566` (`NU-CB-P0-006`) - Implement workflow handoff manifest contract - DONE 2026-06-08
- `TASK-0571` (`NU-CB-P1-011`) - Add procurement/task escalation workflow proposal to workflow catalog

## Historical/reconciled aliases
- `TASK-0574` (`V5-TASK-003`) -> `TASK-0565` - Define feasibility-set workflow semantics
- `TASK-0581` (`V5-TASK-010`) -> `TASK-0566` - Define workflow handoff manifest

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
