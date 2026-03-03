---
id: TASK-0018
epic: EPIC-005
title: "Add Schedule Planning fixture pack + operating model + golden trace placeholders"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa"]
depends_on: ["TASK-0016", "TASK-0017"]
risk: low
---

## Context
A fresh agent should be able to understand the schedule-planning workflow from repo-native materials without reopening external research.

## Objective
- Add a synthetic template pack under `fixtures/workflows/schedule_planning/template_pack/`
- Add `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`
- Add placeholder golden-trace scenarios

## Non-goals
- Do not commit real employee or routing data.
- Do not add runnable optimization notebooks yet.

## Plan
1) Create EMPTY + COMPLETED docx/xlsx artifacts for each stage.
2) Write an operating-model doc explaining planning, publish, and intraday replan semantics.
3) Add placeholder golden trace scenarios for happy path and major replan.

## Files to read first
- `fixtures/workflows/payroll/template_pack/`
- `docs/workflows/schedule_planning/v1/*`

## Files to change
- `fixtures/workflows/schedule_planning/**`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`

## Acceptance criteria
- [ ] Synthetic templates exist for every mapped stage artifact.
- [ ] The operating model explains why the workflow is shaped this way.
- [ ] A fresh agent can infer what “major replan” means and which artifacts it touches.

## Notes
Keep synthetic data realistic enough to show issue handling (no-show, vehicle shortage, delay cluster) without overfitting to one city.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
