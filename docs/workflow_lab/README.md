# Workflow Lab

Workflow Lab is the thin internal candidate-evaluation lane for the repo.

It exists so we can evaluate candidate workflow/process/task behavior outside production while keeping one truth system intact.

## What Workflow Lab is
- an internal-only, non-authoritative lane for evidence about kernel behavior
- a place to compare **execution variants under fixed semantics**
- an input to review, certification, and release decisions

## What Workflow Lab reads
- authoritative workflow packs under `docs/workflows/*/v1/*`
- compiled control derived from those workflow packs
- canonical runtime rows, events, artifacts, and pointers
- reviewed release artifacts and their provenance when promotion/release questions are in scope

## What Workflow Lab emits
- non-authoritative evidence such as reports, freshness summaries, compare packets, and candidate evaluation notes
- artifacts that may inform review/certification/release, but do not directly change production truth

## What Workflow Lab must not become
- no public Workflow Lab API or UI in Phase 0
- no second semantics compiler or peer authored workflow-definition surface
- no direct lab-to-prod runtime mutation
- no raw production DB cloning as a normal workflow
- no `src/onetruth/workflow_lab/` package is required in Phase 0

Prod and lab remain separate environments. Tenant/domain separation inside one environment is not an acceptable substitute.

The healthy promotion path remains:

- `lab -> review/certification/release -> prod`

## Docs in this folder
- [AUTHORITY_BOUNDARY.md](/Users/tylerclark/git/pythonProject/companyos/docs/workflow_lab/AUTHORITY_BOUNDARY.md)
- [PHASED_PLAN.md](/Users/tylerclark/git/pythonProject/companyos/docs/workflow_lab/PHASED_PLAN.md)
- [SCHEMA_PACK.md](/Users/tylerclark/git/pythonProject/companyos/docs/workflow_lab/SCHEMA_PACK.md)

Use these alongside:
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
