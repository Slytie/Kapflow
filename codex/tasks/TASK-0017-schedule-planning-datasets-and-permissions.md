---
id: TASK-0017
epic: EPIC-005
title: "Extend dataset keys + permissions for Schedule Planning roles and artifacts"
status: DONE
owners: ["platform"]
reviewers: ["security", "ops", "qa"]
depends_on: ["TASK-0016", "TASK-0002", "TASK-0004"]
risk: medium
---

## Context
The Schedule Planning workflow introduces new artifact types and review roles (planner, supervisor, operations manager, fleet coordinator) that must use the shared policy vocabulary.

## Objective
- Extend `schemas/artifacts/dataset_keys.yaml` with schedule-planning keys
- Extend `schemas/policy/permissions.yaml` with schedule-planning roles/default rules
- Keep vocabulary generic enough to reuse in future workflows

## Non-goals
- Do not implement a full ABAC policy engine.
- Do not add workflow-specific one-off permission logic in code.

## Plan
1) Add dataset keys with descriptions, kinds, partitioning, and sensitivity.
2) Add roles and default rules for schedule-planning review paths.
3) Check that new roles/actions also make sense with shared task/approval semantics.

## Files to read first
- `schemas/artifacts/dataset_keys.yaml`
- `schemas/policy/permissions.yaml`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`

## Files to change
- `schemas/artifacts/dataset_keys.yaml`
- `schemas/policy/permissions.yaml`

## Acceptance criteria
- [ ] No schedule-planning artifact in the workflow contract uses an undefined dataset key.
- [ ] No schedule-planning approval or task actor lacks a role in the permissions vocabulary.
- [ ] Security agrees the vocabulary stays generic and enforceable.

## Notes
Prefer generic actions and workflow-specific roles over inventing a new action for every business noun.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
