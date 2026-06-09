# EPIC-145 Context Pack - CAPEX real-project fixture governance

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-145` without opening the full master package.
- Keep K12, K3, and blind-validation names as fixture/source-row identifiers, not product namespaces.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
K12-001, K12-002, K12-003, K12-004, SAFE-001, SPB2-T001, SPB2-T002, SPB2-T003, ... (36 tasks total)

## Load first
- `docs/planning/epics/EPIC-145.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## SME-RP fixture-governance notes
- New real-project acceptance gates use `SME-RP`.
- Existing K12/K3/blind task titles and fixture tier names remain where they identify source rows, fixture roles, or raw-data safety boundaries.
- Do not introduce source-specific SME-K12 gate IDs; use `SME-RP-G###` for new real-project acceptance gates.

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
