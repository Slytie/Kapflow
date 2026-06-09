# EPIC-136 Context Pack - CAPEX intake, provenance, and source freeze

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-136` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
MP-PR000, V5-TASK-008, V5-TASK-009, SD-TASK-001, SD-TASK-002, SD-TASK-003, SD-TASK-004, SD-TASK-005, ... plus SME-RP source rows `TASK-0625` and `TASK-0641` remapped to repo `TASK-0648` and `TASK-0664` (12 tasks total)

## SME-RP addendum rows
- Source archive used `SME-K12` labels and proposed `TASK-0625..TASK-0641`; repo-native planning uses `SME-RP` labels and remaps the tranche to `TASK-0648..TASK-0664`.
- `TASK-0648` is closed with conditional, module-specific, non-activation, affected-module-only approval-with-conditions wording.
- `TASK-0664` defines module-specific SME readiness rules.
- K12 remains a fixture-case family only; do not use K12 as an acceptance-gate namespace.

## Historical/reconciled aliases
- `V5-TASK-008` is a reconciled v5 historical alias for `TASK-0582`.
- `V5-TASK-009` is a reconciled v5 historical alias for `TASK-0583`, `TASK-0584`.

## Load first
- `docs/planning/epics/EPIC-136.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
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
