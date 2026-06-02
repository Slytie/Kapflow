# EPIC-146 - CAPEX three-project validation

## Summary
Use the three approved ZIP fixture roles for validation planning without importing raw corpora.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: TP:4.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-145

Context pack:
- `codex/context/EPIC-146.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0589` (`TP-TASK-001`) - Create three-project fixture governance runbook
- `TASK-0590` (`TP-TASK-002`) - Build K12 expected-output manifest from pass11 artifacts
- `TASK-0591` (`TP-TASK-003`) - Build K3 mini-fixture expectation catalog from pass11 artifacts
- `TASK-0597` (`TP-TASK-009`) - Add project-oracle manifest format

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
