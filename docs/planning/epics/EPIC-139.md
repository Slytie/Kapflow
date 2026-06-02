# EPIC-139 - CAPEX domain-boundary cleanup

## Summary
Separate logistics-specific behavior from shared platform semantics before CAPEX surfaces are introduced.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: CLEAN:4, MP:9, NU:1, RF:2, V5:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-137

Context pack:
- `codex/context/EPIC-139.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0245` (`MP-PR012`) - Schedule-control hardening
- `TASK-0246` (`MP-PR013`) - Handoff scaffold and command scopes
- `TASK-0247` (`MP-PR014`) - Weekly seed materialization hardening
- `TASK-0248` (`MP-PR015`) - Live dispatch prepare/activate hardening + republish guard
- `TASK-0249` (`MP-PR016`) - Notify-only/reporting handoff guard
- `TASK-0250` (`MP-PR017`) - Planning-cycle, republish, late-report policy objects
- `TASK-0251` (`MP-PR018`) - Weekly-to-weekly carry-forward
- `TASK-0252` (`MP-PR019`) - Reconciler dry-run only
- `TASK-0253` (`MP-PR020`) - Operator home failure-state surface
- `TASK-0257` (`CLEAN-001`) - Extract logistics side effects from generic approval.respond
- `TASK-0258` (`CLEAN-002`) - Create domain workpage/action descriptor registry
- `TASK-0259` (`CLEAN-003`) - Classify and restructure logistics docs
- `TASK-0260` (`CLEAN-004`) - Split platform tests from logistics regression tests
- `TASK-0369` (`RF-001`) - Approval side-effect extraction
- `TASK-0370` (`RF-002`) - Domain workpage descriptor registry
- `TASK-0561` (`NU-CB-P0-001`) - Extract logistics side effects from approval.respond
- `TASK-0576` (`V5-TASK-005`) - Fix approval.respond domain coupling

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
