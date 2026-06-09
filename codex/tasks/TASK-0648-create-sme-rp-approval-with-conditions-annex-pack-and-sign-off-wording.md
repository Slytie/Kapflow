---
id: TASK-0648
epic: EPIC-136
title: "Create SME-RP approval-with-conditions annex pack and sign-off wording"
status: DONE
completed_at: "2026-06-09T08:50:27Z"
owners: ["capex-product", "capex-architecture"]
reviewers: ["engineering-pm", "capex-sme"]
depends_on: ["TASK-0233"]
risk: high
context_packs: ["codex/context/EPIC-136.md"]
patterns: ["SME-RP acceptance conditions", "module-specific readiness", "no false closure"]
---

# TASK-0648 - Create SME-RP Approval-With-Conditions Annex Pack And Sign-Off Wording

## Why

The source review recommends approval with conditions, not unconditional CAPEX implementation approval. The repo needs generalized SME-RP sign-off wording so the conditions apply across real-project modules, with K12 retained only as the first binding fixture slice.

## Scope

Add SME-RP annex and sign-off planning truth that distinguishes subject-matter target approval from implementation or activation approval.

- Anchor the annex pack under `docs/planning/capex_real_project_acceptance/`.
- Preserve the source archive provenance: original namespace `SME-K12`, source task `TASK-0625`, repo task `TASK-0648`.
- Make `SME-RP-G001` the gate for approval-with-conditions wording.

## Out of scope

- Runtime behavior changes.
- CAPEX runtime/product activation.
- Raw K12, K3, or blind-validation corpus import.
- Treating generated planning artifacts as authoritative project truth.

## Verification

- Contract coverage proves SME-RP gates are present and source SME-K12 gate IDs are not introduced.
- `python3 scripts/validate_repo.py`
- CAPEX progress data validation after regeneration.
- `git diff --check`

## Acceptance criteria

- Annex A-D and the SME-RP register are discoverable from repo planning docs.
- The approval wording says approval is conditional and module-specific.
- No AI output, external status, workpage row, folder path, file presence, PR/PO/invoice, handover, or supplier statement becomes official CAPEX truth without review/approval/adoption.

## Source row mapping

- Source task ID: `TASK-0625`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G001`
- Source conditions: `TOP-01;1-A1;1-A2;15-A1;15-A2;15-A3`

## Closeout evidence

- Added `docs/planning/capex_real_project_acceptance/SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md` as the closeout-grade conditional sign-off wording for `SME-RP-G001`.
- Added machine-readable approval posture fields to `SME_RP_ACCEPTANCE_REGISTER.yaml`: `conditional`, `module_specific`, `non_activation`, and `affected_module_only`.
- Updated the acceptance pack README so the sign-off wording is discoverable with the annex files.
- Added contract coverage proving the approval wording and register posture remain present.
- No runtime activation, migrations, public routes, frontend behavior, raw corpus import, or CAPEX product activation was introduced.
