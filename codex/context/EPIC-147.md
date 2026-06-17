# EPIC-147 Context Pack - CAPEX blind/lab evaluation

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-147` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
TP-TASK-004, TP-TASK-005, TP-TASK-006, TP-TASK-008, TP-TASK-010

## Load first
- `docs/planning/epics/EPIC-147.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## SME-RP fixture-tier notes
- K12, K3, and blind-validation remain fixture tiers for evaluation coverage, overfitting controls, and lab non-authority checks.
- K12 is the first binding real-project fixture suite, but later validation tiers should map back to generalized SME-RP gates instead of creating K12-specific gates.

## Closed blind/scorecard/lab rows
- `TASK-0592` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/BLIND_VALIDATION_FREEZE_PROTOCOL.yaml`.
- `TASK-0593` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/CROSS_PROJECT_INVARIANT_SCORECARD.yaml`.
- `TASK-0594` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/AGENT_LAB_EVAL_MATRIX.yaml`.
- `TASK-0596` is closed as of 2026-06-17 with `docs/planning/capex_three_project_validation/NO_OVERFITTING_REVIEW_CHECKPOINT.yaml`.
- These records define freeze, scorecard, advisory Agent Lab matrix, and no-overfitting checkpoint structure only; `TASK-0598` remains open for CI fixture-tier policy.

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
