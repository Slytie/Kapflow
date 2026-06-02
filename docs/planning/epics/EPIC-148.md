# EPIC-148 - CAPEX off-repo full-corpus, capacity, backup, and restore readiness

## Summary
Prove full-project, off-repo corpus processing and restore/capacity realism before any controlled pilot.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: INGEST:1, SAFE:1, TEST:1, TP:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-138, EPIC-141, EPIC-147

Context pack:
- `codex/context/EPIC-148.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0275` (`INGEST-010`) - Storage quota, backup and restore gate
- `TASK-0306` (`TEST-003`) - Scale benchmark harness and CI/manual gates
- `TASK-0324` (`SAFE-D-001`) - Run full real-corpus capacity, backup, and restore rehearsal before pilot readiness
- `TASK-0595` (`TP-TASK-007`) - Add full-project off-repo runbook for Codex

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
