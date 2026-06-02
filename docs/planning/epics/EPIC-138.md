# EPIC-138 - CAPEX production/lab separation and deploy readiness

## Summary
Keep CAPEX pilot, lab, and production-like activation behind explicit environment and restore gates.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: DEPLOY:2, MP:7, SAFE:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-137, EPIC-100

Context pack:
- `codex/context/EPIC-138.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0241` (`MP-PR008`) - Release build pipeline
- `TASK-0242` (`MP-PR009`) - Backup manifest schema + predeploy backup skeleton
- `TASK-0243` (`MP-PR010`) - Lab-only pilot auth prototype
- `TASK-0244` (`MP-PR011`) - Lab VM deploy pipeline
- `TASK-0254` (`MP-PR021`) - Restore rehearsal automation
- `TASK-0255` (`MP-PR022`) - Reconciler apply mode under role/policy gate
- `TASK-0256` (`MP-PR023`) - Pilot deployment gate
- `TASK-0311` (`DEPLOY-001`) - Storage/DB decision before controlled pilot
- `TASK-0312` (`DEPLOY-002`) - Pilot readiness and rollback gate
- `TASK-0323` (`SAFE-C-001`) - Run full deployment and branch collision review when roadmap is supplied

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
