# EPIC-140 Context Pack - CAPEX project access and membership

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-140` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
PROJ-001, PROJ-002, PROJ-003, PROJ-004, PROJ-005, RF-003, ARCH-W1-T001, ARCH-W1-T002, ... plus SME-RP source rows `TASK-0626` and `TASK-0627` remapped to repo `TASK-0649` and `TASK-0650` (19 tasks total)

## Load first
- `docs/planning/epics/EPIC-140.md`
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

## Current status
- Foundation rows are closed: durable project anchor, direct membership roles, project-bound workflow-run creation, project-scoped child APIs, the first max-five assigned-project selector/dashboard slice, a shared project-scope helper, project-scoped official pointer-family substrate, neutral domain-runtime manifest skeleton, ready-state logistics manifest inventory, incubation-state CAPEX manifest inventory, approval-effect registry shadow parity, project authorization CED, `AuthorizedProjectsQuery` prototype, storage/blob custody CED, pilot storage gate checklist, W1 code pattern register, W1 closeout review, and physical authorization projection runtime state.
- SME-RP addendum rows remain open: `TASK-0649` for CAPEX scope hierarchy and `TASK-0650` for RACI/role-permission mapping. K12 may motivate scope false-closure tests, but scope/RACI rules are generalized real-project contracts.
- CAPEX activation remains blocked outside EPIC-140 by real pilot storage evidence or waiver, raw-corpus/source governance dependencies, richer CAPEX workpage/projection posture, workflow catalog work, release/capacity gates, and production-preflight gates.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
