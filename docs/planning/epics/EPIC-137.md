# EPIC-137 - CAPEX activation blockers and platform readiness

## Summary
Close P0 platform blockers before any CAPEX runtime activation claim.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: MP:7, NU:1, V5:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-136, EPIC-080, EPIC-100

Context pack:
- `codex/context/EPIC-137.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0234` (`MP-PR001`) - Release-bundle cleanliness + Cloud Build PR skeleton
- `TASK-0235` (`MP-PR002`) - Artifact storage safety
- `TASK-0236` (`MP-PR003`) - Transaction composition safety
- `TASK-0237` (`MP-PR004`) - Invariant audit harness and demo audit fixture
- `TASK-0238` (`MP-PR005`) - Canonical generated-artifact helper
- `TASK-0239` (`MP-PR006`) - Shared run/input/edge effect helpers + LogisticsRunResolver
- `TASK-0240` (`MP-PR007`) - Platform Foundation v0 declaration and branch gate
- `TASK-0562` (`NU-CB-P0-002`) - Fix artifact download auth-before-read
- `TASK-0577` (`V5-TASK-006`) - Fix artifact auth-before-read

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
