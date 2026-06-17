# EPIC-146 Context Pack - CAPEX three-project validation

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-146` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
TP-TASK-001, TP-TASK-002, TP-TASK-003, TP-TASK-009 plus SME-RP source row `TASK-0638` remapped to repo `TASK-0661`

## Load first
- `docs/planning/epics/EPIC-146.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## SME-RP fixture-case notes
- `TASK-0661` promotes `K12-T1..T10` as the first binding real-project fixture-case IDs under `SME-RP-G010`.
- K12, K3, and blind-validation are fixture tiers under generalized real-project validation, not acceptance-gate namespaces.

## Closed fixture-governance rows
- `TASK-0589` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md`.
- The runbook records raw/full off-repo handling, sanitized fixture/manifests/hash/aggregate-evidence boundaries, release approval, leak-scan, no-overfitting, and no project-specific hardcoding rules for K12, K3, and blind validation.
- `TASK-0590` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/K12_EXPECTED_OUTPUT_MANIFEST.yaml`.
- `TASK-0591` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml`.
- This is planning-governance evidence only; `TASK-0597` and `TASK-0661` remain open for universal oracle manifest format and binding K12 catalogue work.

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
