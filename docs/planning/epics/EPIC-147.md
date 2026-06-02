# EPIC-147 - CAPEX cross-project invariants, blind validation, and agent lab evaluation

## Summary
Freeze blind-validation rules, cross-project invariant scorecards, agent-lab eval tiers, and no-overfitting checkpoints.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: TP:5.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-110, EPIC-146

Context pack:
- `codex/context/EPIC-147.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0592` (`TP-TASK-004`) - Define blind validation freeze protocol
- `TASK-0593` (`TP-TASK-005`) - Create cross-project invariant scorecard
- `TASK-0594` (`TP-TASK-006`) - Wire agent Lab eval matrix to K12/K3/blind fixture tiers
- `TASK-0596` (`TP-TASK-008`) - Add no-overfitting review checkpoint after blind baseline
- `TASK-0598` (`TP-TASK-010`) - Add fixture tier policy to CI planning

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
