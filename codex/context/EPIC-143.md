# EPIC-143 Context Pack - CAPEX workflow catalog

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-143` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
WFLOW-001, WFLOW-002, WFLOW-003, WFLOW-004, WFLOW-005, WFLOW-006, WFLOW-007, NU-CB-P0-006, ... plus SME-RP source rows `TASK-0631` through `TASK-0634` remapped to repo `TASK-0654` through `TASK-0657` (15 tasks total)

## Historical/reconciled aliases
- `V5-TASK-003` is a reconciled v5 historical alias for `TASK-0565`.
- `V5-TASK-010` is a reconciled v5 historical alias for `TASK-0566`.

## Closed foundation rows
- `TASK-0566` is closed as of 2026-06-08: `capex.workflow_handoff_manifest.v1` and `onetruth.capex_platform.workflow_handoffs` provide an internal handoff manifest contract and validation guard over exact artifact, pointer, SourceRef, validation, closure, task, and workpage basis.
- `TASK-0571` is closed as of 2026-06-17 with a planning-only procurement and CEO escalation proposal that routes decisions through canonical task/approval chains rather than editable workpage status.
- This does not author or activate CAPEX workflow packs.

## SME-RP addendum rows
- `TASK-0654` adds Scope Management workflow requirements.
- `TASK-0655` adds Budget and Commercial Control workflow requirements.
- `TASK-0656` adds Safety and Work Permit Readiness workflow requirements.
- `TASK-0657` classifies workflow extensions as MVP, MVP-lite, or post-MVP before activation claims.

## Load first
- `docs/planning/epics/EPIC-143.md`
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
