# EPIC-140 - CAPEX project access and membership

## Summary
Define project anchors, membership, roles, and project-scoped APIs without crossing tenant/domain boundaries.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Active gated backlog. `TASK-0261` through `TASK-0265`, `TASK-0371`, and `TASK-0381` through `TASK-0382` are closed as the durable project-anchor/direct-membership foundation, first project-scoped child API and selector/dashboard slice, shared project-scope helper, project-scoped official pointer-family substrate, neutral domain-runtime manifest skeleton, and ready-state logistics manifest inventory; authorization projections, CAPEX incubation manifest work, raw-corpus governance, richer CAPEX workpages, and activation remain gated.

## In scope
- Source task families/counts: ARCH:10, NU:1, PROJ:5, RF:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-137, EPIC-139

Context pack:
- `codex/context/EPIC-140.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0261` (`PROJ-001`) - DONE - Decide and implement CAPEX project anchor schema
- `TASK-0262` (`PROJ-002`) - DONE - Implement project_membership and project roles
- `TASK-0263` (`PROJ-003`) - DONE - Project-scoped artifact/task/flag/approval/pointer APIs
- `TASK-0264` (`PROJ-004`) - DONE - Project selector/dashboard for max-five active projects per user
- `TASK-0265` (`PROJ-005`) - DONE - Project-scoped official pointer families
- `TASK-0371` (`RF-003`) - DONE - Project-scope query helper
- `TASK-0381` (`ARCH-W1-T001`) - DONE - Create capex_platform/domain_runtime skeleton
- `TASK-0382` (`ARCH-W1-T002`) - DONE - Inventory logistics domain manifest in ready state
- `TASK-0383` (`ARCH-W1-T003`) - Create CAPEX domain manifest in not-ready/incubation state
- `TASK-0384` (`ARCH-W1-T004`) - Extract generic approval side effects behind registry in shadow mode
- `TASK-0385` (`ARCH-W1-T005`) - Design capex_project and membership schema CED
- `TASK-0386` (`ARCH-W1-T006`) - Implement AuthorizedProjectsQuery prototype and tests
- `TASK-0387` (`ARCH-W1-T007`) - Design storage/blob custody schema CED
- `TASK-0388` (`ARCH-W1-T008`) - Create pilot storage gate checklist
- `TASK-0389` (`ARCH-W1-T009`) - Add architecture snippets and code pattern register
- `TASK-0390` (`ARCH-W1-T010`) - W1 closeout review and old-decision update
- `TASK-0563` (`NU-CB-P0-003`) - Add CAPEX project/membership/authorization runtime state

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
