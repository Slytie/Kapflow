# EPIC-152 Context Pack - CAPEX production preflight

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-152` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
PP-TASK-001, PP-TASK-002, PP-TASK-003, PP-TASK-004, PP-TASK-005, PP-TASK-006, PP-TASK-007, PP-TASK-008

## Load first
- `docs/planning/epics/EPIC-152.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Closed review rows
- `TASK-0599` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/MASTER_Production_Preflight_Review.md`.
- `TASK-0600` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/P0_ACTIVATION_BLOCKER_REVIEW.yaml`.
- `TASK-0601` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml`.
- `TASK-0602` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/RAW_DATA_QUARANTINE_LEAK_SCAN_REVIEW.yaml`.
- `TASK-0603` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/CAPACITY_RESTORE_FULL_CORPUS_REVIEW.yaml`.
- `TASK-0604` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/RELEASE_MIGRATION_ACTIVATION_ROLLBACK_REVIEW.yaml`.
- `TASK-0605` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/SEMANTIC_REVIEW_CI_GATE_REVIEW.yaml`.
- `TASK-0606` is closed as of 2026-06-17 with `docs/planning/capex_production_preflight/PRODUCTION_PREFLIGHT_GO_NO_GO_MEMO.md`.
- These reviews and memo are no-go / blocked planning evidence only; EPIC-152 is complete without production-preflight approval.

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
