# EPIC-147 - CAPEX blind/lab evaluation

## Summary
Define blind validation and lab-eval protocols that prevent overfitting and preserve lab non-authority.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0592` is closed with the blind validation freeze protocol, `TASK-0593` is closed with the cross-project invariant scorecard structure, `TASK-0594` is closed with advisory Agent Lab eval matrix wiring, and `TASK-0596` is closed with the no-overfitting review checkpoint structure.

## In scope
- Source task families/counts: TP:5.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Treat K12, K3, and blind validation as fixture tiers under generalized real-project validation.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-146, EPIC-110

Context pack:
- `codex/context/EPIC-147.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0592` (`TP-TASK-004`) - Define blind validation freeze protocol - DONE 2026-06-17
- `TASK-0593` (`TP-TASK-005`) - Create cross-project invariant scorecard - DONE 2026-06-17
- `TASK-0594` (`TP-TASK-006`) - Wire agent Lab eval matrix to K12/K3/blind fixture tiers - DONE 2026-06-17
- `TASK-0596` (`TP-TASK-008`) - Add no-overfitting review checkpoint after blind baseline - DONE 2026-06-17
- `TASK-0598` (`TP-TASK-010`) - Add fixture tier policy to CI planning

## Blind validation, scorecard, and Agent Lab addendum
- `TASK-0592` records `docs/planning/capex_three_project_validation/BLIND_VALIDATION_FREEZE_PROTOCOL.yaml` as planning evidence for `TP-TASK-004`.
- `TASK-0593` records `docs/planning/capex_three_project_validation/CROSS_PROJECT_INVARIANT_SCORECARD.yaml` as planning evidence for `TP-TASK-005`.
- `TASK-0594` records `docs/planning/capex_three_project_validation/AGENT_LAB_EVAL_MATRIX.yaml` as planning evidence for `TP-TASK-006`.
- `TASK-0596` records `docs/planning/capex_three_project_validation/NO_OVERFITTING_REVIEW_CHECKPOINT.yaml` as planning evidence for `TP-TASK-008`.
- The protocol, scorecard, eval matrix, and checkpoint define freeze, custody, status, waiver, invariant, fixture-tier, lab non-authority, and no-overfitting review structures only; they do not run blind validation, pass `TP-G08` or `TP-G11`, approve fixture release, create official pointers or approvals, approve production preflight, or activate CAPEX.

## SME-RP real-project acceptance addendum
- K12, K3, and blind-validation remain fixture tiers for evaluation coverage and overfitting controls.
- The K12 fixture suite is the first binding real-project slice, but blind/lab evaluation must keep future tiers mapped to generalized SME-RP gates rather than K12-specific gates.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
