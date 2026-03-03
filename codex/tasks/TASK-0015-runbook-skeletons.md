---
id: TASK-0015
epic: EPIC-080
title: "Add runbook skeletons for predictable failure modes"
status: DONE
owners: ["sre"]
reviewers: ["platform"]
depends_on: ["TASK-0007"]
risk: medium
---

## Context
SRE gate requires minimally useful runbooks. Add skeletons early so they are not retrofits.

## Objective
- Add runbook stubs under `docs/ops/runbooks/` for:
  - audit degraded mode
  - stuck run/task
  - export backlog
  - isolation incident response


## Plan
1) Create runbook files.
2) Include 'Symptoms', 'Immediate checks', 'Mitigation', 'Escalation'.

## Files to read first
- `docs/planning/checklists/SRE_SIGNOFF.md`

## Files to change
- `docs/ops/runbooks/*.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Runbooks exist and match alert categories.
- [ ] SRE can use them as a starting point.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
