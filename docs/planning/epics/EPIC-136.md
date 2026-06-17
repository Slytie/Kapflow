# EPIC-136 - CAPEX intake, provenance, and source freeze

## Summary
Own the v6 intake record, source-package provenance, task conversion, and source-freeze gates.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0582` and `TASK-0583` are closed with the CAPEX Product Goal, metric stack, and vertical-slice ladder; `TASK-0648` is closed with SME-RP approval-with-conditions sign-off wording; `TASK-0664` is closed with the module-specific readiness rule.

## In scope
- Source task families/counts: MP:1, SD:7, SME-RP:2, V5:2.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Preserve the imported real-project acceptance-condition tranche under the generalized `SME-RP` namespace.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-080

Context pack:
- `codex/context/EPIC-136.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0233` (`MP-PR000`) - Red-team integration update
- `TASK-0582` (`SD-TASK-001`) - Define CAPEX Product Goal and metric stack - DONE 2026-06-17
- `TASK-0583` (`SD-TASK-002`) - Create CAPEX vertical-slice ladder - DONE 2026-06-17
- `TASK-0584` (`SD-TASK-003`) - Add dependency register and risk-based milestone overlay
- `TASK-0585` (`SD-TASK-004`) - Add backlog hierarchy and story decomposition templates
- `TASK-0586` (`SD-TASK-005`) - Define delivery operating cadence
- `TASK-0587` (`SD-TASK-006`) - Add first-90-days execution overlay
- `TASK-0588` (`SD-TASK-007`) - Add Definition of Ready / Done for CAPEX task classes
- `TASK-0648` (`SME-RP:TASK-0625`) - DONE - Create SME-RP approval-with-conditions annex pack and sign-off wording
- `TASK-0664` (`SME-RP:TASK-0641`) - DONE - Add module-specific SME readiness rule

## Historical/reconciled aliases
- `TASK-0579` (`V5-TASK-008`) -> `TASK-0582` - Add Product Goal and metric stack
- `TASK-0580` (`V5-TASK-009`) -> `TASK-0583`, `TASK-0584` - Add vertical-slice ladder and dependency register

## SME-RP real-project acceptance addendum
- The source archive used `SME-K12` labels and proposed source rows `TASK-0625` through `TASK-0641`; this repo generalizes the tranche as `SME-RP` and remaps it to `TASK-0648` through `TASK-0664`.
- `SME-RP` means Subject-Matter / Real-Project acceptance conditions. K12 is the first binding fixture slice, not the CAPEX product model.
- `TASK-0648` records approval-with-conditions as conditional, module-specific, non-activation, and affected-module-only sign-off wording.
- `TASK-0664` records `SME-RP-MODULE-READINESS-RULE.v1`; the module-specific readiness rule is recorded per workflow, workpage family, projection family, snapshot/export surface, and external-observation surface before any CAPEX module can claim readiness.
- Unresolved business definitions, RACI posture, or workflow-extension classification block only dependent modules and surfaces; independent platform hardening, schema parity, security fixes, neutral foundation work, and disabled CAPEX scaffolding may continue.

## Delivery governance addendum
- `TASK-0582` records the CAPEX Product Goal and metric stack under `docs/planning/capex_delivery/` as repo planning-governance evidence only.
- `TASK-0583` records the first vertical-slice ladder (`VS-00` through `VS-05`) with entry/exit gates, metric refs, repo evidence refs, and planning-only activation posture.
- `TASK-0584` remains open for the dependency register and risk-based milestone overlay; the vertical-slice ladder does not close dependency/risk milestone work.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
