# EPIC-142 Context Pack - CAPEX artifact promotion and governance

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-142` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
ART-001, ART-003, ART-004, ART-005, ART-006, RF-007, RF-008, ARCH-W4-S01, ... (32 tasks total)

## Historical/reconciled aliases
- `V5-TASK-001` is a reconciled v5 historical alias for `TASK-0447`, `TASK-0565`, `TASK-0305`.
- `V5-TASK-002` is a reconciled v5 historical alias for `TASK-0392`, `TASK-0373`.
- `V5-TASK-004` is a reconciled v5 historical alias for `TASK-0305`, `TASK-0565`.

## Load first
- `docs/planning/epics/EPIC-142.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

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
