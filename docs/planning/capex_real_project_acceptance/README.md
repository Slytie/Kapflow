# CAPEX real-project acceptance conditions

This directory records the generalized subject-matter / real-project acceptance
conditions imported from the June 2026 CAPEX planning update.

## Namespace

The repo namespace is `SME-RP`: subject-matter / real-project acceptance.

The source archive used `SME-K12` labels and proposed `TASK-0625` through
`TASK-0641`. The repo intentionally generalizes the acceptance namespace and
remaps the task range to `TASK-0648` through `TASK-0664` to avoid collisions
with existing repo-native task IDs.

## Boundary

- K12 remains the first binding real-project fixture slice.
- `K12-T1` through `K12-T10` are fixture-case IDs, not the product model.
- K3, K12, and blind validation corpora remain off-repo except for sanitized
  fixtures, manifests, hashes, and aggregate evidence.
- These docs do not activate CAPEX runtime behavior, public CAPEX workpages,
  raw corpus ingest, production deployment, or any second truth system.

## Files

- `SME_RP_ACCEPTANCE_REGISTER.yaml` - machine-readable gates, task remap,
  fixture cases, risks, and workflow classification.
- `SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md` - conditional,
  module-specific, non-activation sign-off wording for `SME-RP-G001`.
- `ANNEX_A_STATUS_MODEL_AND_RACI_DRAFT.md` - status and role-permission draft.
- `ANNEX_B_MANDATORY_FIELDS_AND_ESCALATION_THRESHOLDS_DRAFT.md` - commercial
  fields and escalation threshold families.
- `ANNEX_C_REAL_PROJECT_BINDING_ACCEPTANCE_CATALOGUE.md` - K12 fixture cases as
  the first binding real-project acceptance slice.
- `ANNEX_D_WORKFLOW_EXTENSION_CLASSIFICATION.md` - MVP / MVP-lite / post-MVP
  classification for subject-matter workflow extensions.
