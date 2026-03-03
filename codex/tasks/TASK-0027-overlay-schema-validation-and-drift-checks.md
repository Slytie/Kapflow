---
id: TASK-0027
epic: EPIC-080
title: "Implement full authored-surface validation and drift checks"
status: DONE
owners:
- sre
- platform
reviewers:
- security
- qa
depends_on:
- TASK-0025
- TASK-0034
risk: high
context_packs: []
patterns:
- PATTERN-007
- PATTERN-008
---

## Context
The repo validates the execution overlay, but the higher-authority workflow-pack surface still lacks full machine validation. That leaves room for drift across workflow contracts, artifact maps, registries, tasks, and planning references.

## Objective
Add validation and freshness checks for the full authored workflow surface, not just the overlay files.

## Non-goals
- Do not build runtime services.
- Do not invent new workflow semantics in validator code.
- Do not treat generated derivatives as authoritative inputs.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/STAGE4_PLAN.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/payroll/v1/ARTIFACT_MAP.yaml`
- `schemas/artifacts/dataset_keys.yaml`
- `schemas/events/event_type_registry.yaml`
- `schemas/agentic/decision_catalog.schema.json`
- `schemas/agentic/execution_profile.schema.json`
- `docs/planning/TASK_INDEX.md`

## Context packs / patterns to consult
- `PATTERN-007`
- `PATTERN-008`

## Source files to change
- `schemas/` (new workflow-pack schemas if needed)
- `docs/workflows/*/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/*/v1/ARTIFACT_MAP.yaml`
- `docs/planning/TASK_INDEX.md` if stale references are found
- validation scripts / CI wiring when they appear

## Generated / downstream artifacts impacted
- generated runbook packs
- CompanyOS IR
- approval packets
- source-hash/freshness manifests

## Plan
1. Define the validation boundary for workflow contracts and artifact maps.
2. Enforce cross-file alignment across stage IDs, dataset keys, actions, decision refs, and required events.
3. Add explicit policy for out-of-scope dataset keys and stale planning/task references.
4. Wire the checks into the repo validation path.

## Verification
- Parse all workflow packs successfully.
- Validate decision catalogs and execution profiles against their schemas.
- Run the authored-surface validator and confirm it catches a seeded mismatch.
- Confirm stale path/reference checks fail on broken task links.

## Acceptance criteria
- workflow contracts and artifact maps are machine-validated
- cross-file drift across workflow packs, registries, and planning refs is detectable
- out-of-scope dataset-key policy is explicit and enforced
- validator output is suitable for CI blocking checks

## Notes / decisions
This task should preserve the authority hierarchy: workflow packs first, overlays next, generated derivatives last.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
