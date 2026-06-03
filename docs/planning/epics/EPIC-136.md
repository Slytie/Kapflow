# EPIC-136 - CAPEX intake, provenance, and source freeze

## Summary
Own the v6 intake record, source-package provenance, task conversion, and source-freeze gates.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: MP:1, SD:7, V5:2.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
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

## Task stack
- `TASK-0233` (`MP-PR000`) - Red-team integration update
- `TASK-0582` (`SD-TASK-001`) - Define CAPEX Product Goal and metric stack
- `TASK-0583` (`SD-TASK-002`) - Create CAPEX vertical-slice ladder
- `TASK-0584` (`SD-TASK-003`) - Add dependency register and risk-based milestone overlay
- `TASK-0585` (`SD-TASK-004`) - Add backlog hierarchy and story decomposition templates
- `TASK-0586` (`SD-TASK-005`) - Define delivery operating cadence
- `TASK-0587` (`SD-TASK-006`) - Add first-90-days execution overlay
- `TASK-0588` (`SD-TASK-007`) - Add Definition of Ready / Done for CAPEX task classes

## Historical/reconciled aliases
- `TASK-0579` (`V5-TASK-008`) -> `TASK-0582` - Add Product Goal and metric stack
- `TASK-0580` (`V5-TASK-009`) -> `TASK-0583`, `TASK-0584` - Add vertical-slice ladder and dependency register

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
