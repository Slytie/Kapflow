---
id: TASK-0010
epic: EPIC-050
title: "Define human task claim lease semantics (to prevent stuck work)"
status: DONE
owners: ["platform", "sre"]
reviewers: ["security", "ops", "qa"]
depends_on: ["TASK-0002", "TASK-0003"]
risk: high
---

## Context
Claim semantics without leases/timeouts creates silent stalls. We need explicit lease rules and required timeline events.

## Objective
- Create `docs/architecture/human_task_semantics.md` covering:
  - task states
  - claim atomicity
  - lease duration + heartbeat
  - forced unclaim
  - SLA escalation timer (one MVP timer)


## Plan
1) Define state machine.
2) Define fields: claimed_by, claimed_until.
3) Define required events for each transition.
4) Define one escalation rule.

## Files to read first
- `docs/architecture/invariants.md`
- `docs/planning/epics/EPIC-050.md`

## Files to change
- `docs/architecture/human_task_semantics.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Semantics are unambiguous and support acceptance tests.
- [ ] Ops agrees escalation behavior is acceptable for MVP.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
