---
id: TASK-0016
epic: EPIC-005
title: "Freeze Schedule Planning workflow contract v1 into YAML + acceptance criteria"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa", "security"]
depends_on: ["TASK-0001"]
risk: medium
---

## Context
We need a second workflow contract pack that matches the operating reality of same-day delivery scheduling without changing the shared platform invariants.

## Objective
- Create/confirm `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- Create/confirm `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- Create/confirm `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`

## Non-goals
- Do not implement optimization code.
- Do not create dispatcher UI designs.
- Do not hard-code jurisdiction-specific labor-law rules.

## Plan
1) Freeze stage boundaries and partition key.
2) Define official inputs/outputs and approval points.
3) Encode publish vs replan semantics.
4) Write acceptance criteria for happy path + negative cases.

## Files to read first
- `docs/planning/STAGE4_PLAN.md`
- `docs/architecture/invariants.md`
- `docs/workflows/payroll/v1/*`

## Files to change
- `docs/workflows/schedule_planning/v1/*`

## Commands to run
- (None yet; doc-only task)

## Acceptance criteria
- [ ] Ops can read the contract and agree it matches real schedule-planning work.
- [ ] QA can derive acceptance tests from the criteria.
- [ ] No ambiguity about official inputs/outputs and publish/replan behavior.

## Notes
Keep the workflow general enough for multiple hubs, but concrete enough for a same-day delivery operator.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
