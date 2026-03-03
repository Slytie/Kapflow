---
id: TASK-0009
epic: EPIC-030
title: "Specify promotion drift detection semantics and event payload"
status: DONE
owners: ["platform"]
reviewers: ["security", "ops", "qa"]
depends_on: ["TASK-0006"]
risk: medium
---

## Context
Loose promotion is allowed, but drift must be visible and recorded. We need explicit semantics for drift detection.

## Objective
- Create `docs/architecture/promotion_semantics.md` defining:
  - reviewed_version_id vs promoted_version_id
  - drift detection conditions
  - required timeline events and UI flag


## Plan
1) Write clear definitions.
2) Add example scenarios.
3) Update acceptance criteria to reference this doc if needed.

## Files to read first
- `docs/workflows/payroll/v1/ACCEPTANCE_CRITERIA.md`

## Files to change
- `docs/architecture/promotion_semantics.md`
- (optional) acceptance criteria updates

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Drift semantics are explicit and testable.
- [ ] Ops agrees on user-facing interpretation.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
