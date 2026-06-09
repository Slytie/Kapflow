# EPIC-151 Context Pack - CAPEX transparency and snapshots

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-151` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
ART-002, WFLOW-008, ARCH-W8-S01, ARCH-W8-S02, ARCH-W8-S03, ARCH-W8-S04, ARCH-W8-S05, ARCH-W8-S06, ... plus SME-RP source rows `TASK-0636` and `TASK-0640` remapped to repo `TASK-0659` and `TASK-0663` (29 tasks total)

## Current closeout notes
- `TASK-0569` is closed as of 2026-06-09: `onetruth.capex_platform.interface_burden` validates that interface obligations are owned, transferred, waived, accepted residual, or open with a traceable follow-up. This is an internal policy/helper only, not public routing or CAPEX activation.

## SME-RP addendum rows
- `TASK-0659` defines procurement fields and executive escalation thresholds under `SME-RP-G006` and `SME-RP-G007`.
- `TASK-0663` defines external-system mode taxonomy under `SME-RP-G011`.
- External status is observation/input only unless canonical internal state promotes a reviewed claim.

## Load first
- `docs/planning/epics/EPIC-151.md`
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
