---
id: TASK-0001
epic: EPIC-000
title: "Freeze Payroll workflow contract v1 into YAML + acceptance criteria"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa", "security"]
depends_on: []
risk: medium
---

## Context
We must freeze the reference workflow contract before building implementation.
Use the payroll template pack under `fixtures/workflows/payroll/template_pack/`.

## Objective
- Create/confirm `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- Create/confirm `docs/workflows/payroll/v1/ARTIFACT_MAP.yaml`
- Create/confirm `docs/workflows/payroll/v1/ACCEPTANCE_CRITERIA.md`

## Non-goals
- Do not implement payroll calculations.
- Do not create UI designs.

## Plan
1) Review template pack stage list and artifacts.
2) Confirm which stages are in MVP slice.
3) Confirm dataset_keys and roles (official_input/output/evidence).
4) Update acceptance criteria with payroll-specific constraints (masked bank details, Lock_ID).

## Files to read first
- `fixtures/workflows/payroll/template_pack/00_Payroll_Workflow_and_Artifact_Templates.docx`
- `docs/planning/STAGE4_PLAN.md`
- `docs/architecture/invariants.md`

## Files to change
- `docs/workflows/payroll/v1/*`
- `schemas/artifacts/dataset_keys.yaml` (if needed)

## Commands to run
- (None yet; doc-only task)

## Acceptance criteria
- [ ] Ops can read the contract and agree it matches the real workflow.
- [ ] QA can derive acceptance tests from the criteria.
- [ ] No ambiguity about official inputs/outputs at each stage.

## Notes
Record any “scope cut” decisions explicitly (what is out-of-scope and why).

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
