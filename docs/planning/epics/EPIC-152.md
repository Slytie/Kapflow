# EPIC-152 - CAPEX production preflight

## Summary
Verify P0 blockers, three-project evidence, raw-data quarantine, restore, release, and go/no-go readiness.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0599` is closed with a no-go / blocked master production-preflight review, `TASK-0600` is closed with P0 activation blocker review evidence, and `TASK-0601` is closed with three-project evidence package review evidence; remaining gate-specific checks and the final go/no-go memorandum remain open.

## In scope
- Source task families/counts: PP:8.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-137, EPIC-146, EPIC-148, EPIC-150

Context pack:
- `codex/context/EPIC-152.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0599` (`PP-TASK-001`) - Run production preflight readiness review - DONE 2026-06-17
- `TASK-0600` (`PP-TASK-002`) - Verify P0 activation blockers are closed or explicitly waived - DONE 2026-06-17
- `TASK-0601` (`PP-TASK-003`) - Verify three-project evidence package - DONE 2026-06-17
- `TASK-0602` (`PP-TASK-004`) - Verify raw-data quarantine and leak-scan evidence
- `TASK-0603` (`PP-TASK-005`) - Verify capacity, backup, restore, and off-repo full-corpus run evidence
- `TASK-0604` (`PP-TASK-006`) - Verify release bundle, migration lanes, activation gates, and rollback/compensation evidence
- `TASK-0605` (`PP-TASK-007`) - Verify semantic MR, CODEOWNERS, review-tier, and CI gates are active
- `TASK-0606` (`PP-TASK-008`) - Produce production preflight go/no-go memorandum

## Production-preflight master review addendum
- `TASK-0599` records `docs/planning/capex_production_preflight/MASTER_Production_Preflight_Review.md` as planning evidence for `PP-TASK-001`.
- `TASK-0600` records `docs/planning/capex_production_preflight/P0_ACTIVATION_BLOCKER_REVIEW.yaml` as no-go / blocked review evidence for `PP-TASK-002`.
- `TASK-0601` records `docs/planning/capex_production_preflight/THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml` as no-go / blocked review evidence for `PP-TASK-003`.
- The master review result remains `no_go_blocked_pending_evidence`; `PROD-PRE-G01..G05` are reviewed but blocked, and `PROD-PRE-G06..G10` remain blocked pending `TASK-0602..TASK-0606`.
- This review does not approve waivers, pilot readiness, production readiness, the final go/no-go memo, raw corpus import, public routes, workflow activation, or CAPEX runtime/product activation.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
