# EPIC-150 - CAPEX release governance, documentation, and repo hygiene

## Summary
Create the CAPEX release/documentation/refactor governance layer and keep branch, docs, and review policy explicit.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: ARCH:24, DOC:3, RF:2, SAFE:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-138, EPIC-149

Context pack:
- `codex/context/EPIC-150.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0308` (`DOC-001`) - Restructure documentation tree
- `TASK-0309` (`DOC-002`) - Development flow and task template adoption
- `TASK-0310` (`DOC-003`) - Code review and refactor gate adoption
- `TASK-0314` (`SAFE-002`) - Safety Pass B: deployment roadmap/branch collision review
- `TASK-0379` (`RF-011`) - Feature flag retirement register
- `TASK-0380` (`RF-012`) - Docs route/status cleanup
- `TASK-0513` (`ARCH-W7-SL-001`) - Branch class manifest and classifier
- `TASK-0514` (`ARCH-W7-SL-002`) - Release bundle manifest schema
- `TASK-0515` (`ARCH-W7-SL-003`) - Migration lane manifest schema
- `TASK-0516` (`ARCH-W7-SL-004`) - Migration compatibility test scaffold
- `TASK-0517` (`ARCH-W7-SL-005`) - Feature gate manifest and activation model
- `TASK-0518` (`ARCH-W7-SL-006`) - Activation guard helper
- `TASK-0519` (`ARCH-W7-SL-007`) - Compensation plan schema
- `TASK-0520` (`ARCH-W7-SL-008`) - Docs authority schema
- `TASK-0521` (`ARCH-W7-SL-009`) - Docs authority linter
- `TASK-0522` (`ARCH-W7-SL-010`) - CED template and lifecycle metadata
- `TASK-0523` (`ARCH-W7-SL-011`) - Semantic task template
- `TASK-0524` (`ARCH-W7-SL-012`) - Semantic MR evidence bundle
- `TASK-0525` (`ARCH-W7-SL-013`) - Semantic CODEOWNERS sketch
- `TASK-0526` (`ARCH-W7-SL-014`) - Path-based semantic merge gate
- `TASK-0527` (`ARCH-W7-SL-015`) - Forbidden state transition lint rules
- `TASK-0528` (`ARCH-W7-SL-016`) - Fixture leakage release gate
- `TASK-0529` (`ARCH-W7-SL-017`) - AI assistance declaration in MR
- `TASK-0530` (`ARCH-W7-SL-018`) - Release readiness gate script
- `TASK-0531` (`ARCH-W7-SL-019`) - Activation approval record
- `TASK-0532` (`ARCH-W7-SL-020`) - Post-activation smoke evidence
- `TASK-0533` (`ARCH-W7-SL-021`) - Quality metrics dashboard spec
- `TASK-0534` (`ARCH-W7-SL-022`) - Refactor work item register integration
- `TASK-0535` (`ARCH-W7-SL-023`) - Implementation history check
- `TASK-0536` (`ARCH-W7-SL-024`) - Wave 7 integration QA

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
