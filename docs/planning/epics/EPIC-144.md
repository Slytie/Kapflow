# EPIC-144 - CAPEX workpages, projections, and stale command guards

## Summary
Add CAPEX project workpages over backend-owned projections and command envelopes without creating UI-local truth.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: ARCH:20, ART:1, NU:1, RF:1, WP:9.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-120, EPIC-143, EPIC-142

Context pack:
- `codex/context/EPIC-144.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0282` (`ART-007`) - Implement projection consistency test manifest
- `TASK-0291` (`WP-001`) - CAPEX project dashboard and shell
- `TASK-0292` (`WP-002`) - Project Intake workpage
- `TASK-0293` (`WP-003`) - Corpus Baseline / Packet Review workpage
- `TASK-0294` (`WP-004`) - Commitment Chain workpage
- `TASK-0295` (`WP-005`) - Assumption Closure workpage
- `TASK-0296` (`WP-006`) - Interface Resolution workpage
- `TASK-0297` (`WP-007`) - Flags / Tasks / Review Queue workpage
- `TASK-0298` (`WP-008`) - Pointer Promotion workpage
- `TASK-0299` (`WP-009`) - Risk / Stale / CEO Cockpit
- `TASK-0377` (`RF-009`) - Workpage projection/command split
- `TASK-0449` (`ARCH-W5-S01`) - Projection table design note and CED approval
- `TASK-0450` (`ARCH-W5-S02`) - Projection invalidation table migration draft
- `TASK-0451` (`ARCH-W5-S03`) - Projection snapshot/row schema draft
- `TASK-0452` (`ARCH-W5-S04`) - Projection job token-guard prototype
- `TASK-0453` (`ARCH-W5-S05`) - Signed cursor codec prototype
- `TASK-0454` (`ARCH-W5-S06`) - Workpage read API contract
- `TASK-0455` (`ARCH-W5-S07`) - Batch hydration service skeleton
- `TASK-0456` (`ARCH-W5-S08`) - Project dashboard projection family
- `TASK-0457` (`ARCH-W5-S09`) - Artifact packet review projection family
- `TASK-0458` (`ARCH-W5-S10`) - Flag/task queue projection family
- `TASK-0459` (`ARCH-W5-S11`) - Approval/waiver queue projection family
- `TASK-0460` (`ARCH-W5-S12`) - Workpage command envelope schema
- `TASK-0461` (`ARCH-W5-S13`) - Command dispatch skeleton
- `TASK-0462` (`ARCH-W5-S14`) - Stale command rejection tests
- `TASK-0463` (`ARCH-W5-S15`) - ProjectWorkpageProvider frontend skeleton
- `TASK-0464` (`ARCH-W5-S16`) - Query performance battery harness
- `TASK-0465` (`ARCH-W5-S17`) - No generic status command lint/test rule
- `TASK-0466` (`ARCH-W5-S18`) - Workpage family registry
- `TASK-0467` (`ARCH-W5-S19`) - Projection observability/admin view design
- `TASK-0468` (`ARCH-W5-S20`) - Wave 5 refactor/closeout pass
- `TASK-0567` (`NU-CB-P0-007`) - Add CAPEX projection snapshot and stale-command test harness

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
