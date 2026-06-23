# EPIC-142 - CAPEX artifact promotion and governance

## Summary
Constrain generated artifacts, pointer promotion, closure, stale reopen, and waiver behavior.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0565` is closed as of 2026-06-08 with internal closure/waiver/stale runtime primitive evidence, `TASK-0276` is closed as of 2026-06-17 with the CAPEX generated artifact envelope schema and canonical naming helper, `TASK-0278` is closed as of 2026-06-17 with generated artifact schema/bundle validator evidence, `TASK-0570` is closed as of 2026-06-17 with non-commutative closure and pointer sequence tests, and `TASK-0651` is closed with the SME-RP evidence status transition contract. Meaningful SourceRef/evidence policy, pointer-promotion policy checks, richer closure command/UI surfaces, AI trust, and partial-handover addenda remain open.

## In scope
- Source task families/counts: ARCH:20, ART:5, NU:2, RF:2, SME-RP:3, V5:3.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Define generalized evidence status, AI trust, partial handover, observation phase, and closure-dimension governance.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-141

Context pack:
- `codex/context/EPIC-142.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0276` (`ART-001`) - Implement generated artifact envelope and canonical naming - DONE 2026-06-17
- `TASK-0278` (`ART-003`) - Implement schema and bundle validators - DONE 2026-06-17
- `TASK-0279` (`ART-004`) - Implement meaningful source_refs/evidence_refs policy
- `TASK-0280` (`ART-005`) - Implement pointer promotion request and policy checks
- `TASK-0281` (`ART-006`) - Implement stale/reopen register and rules
- `TASK-0375` (`RF-007`) - Generated artifact helper migration
- `TASK-0376` (`RF-008`) - Pointer promotion validator isolation
- `TASK-0429` (`ARCH-W4-S01`) - Create CED and schema draft for ApprovalResponse and approval.respond domain neutrality.
- `TASK-0430` (`ARCH-W4-S02`) - Implement ApprovalResponse append-only record and TimelineEvent emission.
- `TASK-0431` (`ARCH-W4-S03`) - Extract generic approval side-effect hooks into explicit domain hook registry with capability allowlist.
- `TASK-0432` (`ARCH-W4-S04`) - Implement Waiver object and lifecycle.
- `TASK-0433` (`ARCH-W4-S05`) - Implement waiver scope matcher and expiry/revocation checks.
- `TASK-0434` (`ARCH-W4-S06`) - Implement PolicyDecision and PolicyDecisionRuleResult with severity/mode and satisfied_by_waiver.
- `TASK-0435` (`ARCH-W4-S07`) - Implement local policy evaluator trace with input digest and redacted snapshot references.
- `TASK-0436` (`ARCH-W4-S08`) - Implement ClosureGateEvaluation object.
- `TASK-0437` (`ARCH-W4-S09`) - Implement closure evaluator for initial K12 dimensions.
- `TASK-0438` (`ARCH-W4-S10`) - Implement ClosureSnapshot append-only record with basis_version_vector.
- `TASK-0439` (`ARCH-W4-S11`) - Implement close command chain from PolicyDecision to ClosureSnapshot.
- `TASK-0440` (`ARCH-W4-S12`) - Implement force_close_with_residuals path.
- `TASK-0441` (`ARCH-W4-S13`) - Implement ClosureBasisRef for delayed callbacks and workpage commands.
- `TASK-0442` (`ARCH-W4-S14`) - Implement stale callback rejection and rebase task creation.
- `TASK-0443` (`ARCH-W4-S15`) - Implement StaleReopenRuleRegistry schema and action precedence.
- `TASK-0444` (`ARCH-W4-S16`) - Implement stale/reopen evaluator and dependency lookup over closure basis.
- `TASK-0445` (`ARCH-W4-S17`) - Add workpage command envelope validation for closure/reopen/promote commands.
- `TASK-0446` (`ARCH-W4-S18`) - Add no-false-closure acceptance matrix.
- `TASK-0447` (`ARCH-W4-S19`) - Patch architecture docs and code review checklist with W4 governance checks.
- `TASK-0448` (`ARCH-W4-S20`) - Remove/retire any generic approval handler domain side effects after hook registry migration.
- `TASK-0565` (`NU-CB-P0-005`) - Add ClosureGateEvaluation, ClosureSnapshot, Waiver, lifecycle recurrence stale rules - DONE 2026-06-08
- `TASK-0570` (`NU-CB-P1-010`) - Add non-commutative artifact sequence tests - DONE 2026-06-17
- `TASK-0651` (`SME-RP:TASK-0628`) - DONE - Harden evidence status vocabulary and transition rules
- `TASK-0658` (`SME-RP:TASK-0635`) - Extend closure model with partial handover and observation phase
- `TASK-0660` (`SME-RP:TASK-0637`) - Align AI trust status and source binding requirements

## Historical/reconciled aliases
- `TASK-0572` (`V5-TASK-001`) -> `TASK-0447`, `TASK-0565`, `TASK-0305` - Patch master architecture: reality vs representation
- `TASK-0573` (`V5-TASK-002`) -> `TASK-0392`, `TASK-0373` - Add canonical relation_kind vocabulary
- `TASK-0575` (`V5-TASK-004`) -> `TASK-0305`, `TASK-0565` - Define issue/hypothesis graph guardrails

## SME-RP real-project acceptance addendum
- Evidence status vocabulary, AI trust states, partial handover, observation phase, and closure dimensions are CAPEX governance primitives, not K12-specific exceptions.
- `TASK-0651` records the evidence-link vocabulary as proposed, under review, valid, partly valid, contradictory, obsolete, invalid, insufficient, and accepted with residual risk, with closure eligibility controlled by explicit review state.
- AI outputs must remain draft, assistant-suggested, or reviewer-adopted until a human or approved policy path binds them to source evidence under `SME-RP-G004` and `SME-RP-G009`.
- Partial handover and observation-phase closure must preserve residuals, scope exclusions, owner accountability, reopening triggers, and executive visibility under `SME-RP-G008`.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
