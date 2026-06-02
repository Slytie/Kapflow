# EPIC-152 - CAPEX production preflight go/no-go

## Summary
Run the final production preflight evidence review without confusing deployed code with activated truth mutation.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: PP:8.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-136..EPIC-151

Context pack:
- `codex/context/EPIC-152.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0599` (`PP-TASK-001`) - Run production preflight readiness review
- `TASK-0600` (`PP-TASK-002`) - Verify P0 activation blockers are closed or explicitly waived
- `TASK-0601` (`PP-TASK-003`) - Verify three-project evidence package
- `TASK-0602` (`PP-TASK-004`) - Verify raw-data quarantine and leak-scan evidence
- `TASK-0603` (`PP-TASK-005`) - Verify capacity, backup, restore, and off-repo full-corpus run evidence
- `TASK-0604` (`PP-TASK-006`) - Verify release bundle, migration lanes, activation gates, and rollback/compensation evidence
- `TASK-0605` (`PP-TASK-007`) - Verify semantic MR, CODEOWNERS, review-tier, and CI gates are active
- `TASK-0606` (`PP-TASK-008`) - Produce production preflight go/no-go memorandum

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
