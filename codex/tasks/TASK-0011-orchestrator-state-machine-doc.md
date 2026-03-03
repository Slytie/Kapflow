---
id: TASK-0011
epic: EPIC-040
title: "Document run/task state machines for payroll slice (WAIT/resume/retry/stale)"
status: DONE
owners: ["platform"]
reviewers: ["qa", "sre", "security"]
depends_on: ["TASK-0001", "TASK-0003", "TASK-0009"]
risk: high
---

## Context
Before coding the orchestrator, document the run and task state machines so implementation is not ad-hoc.

## Objective
- Create `docs/architecture/orchestration_semantics.md` describing:
  - run states and transitions
  - WAIT conditions and wakeup triggers
  - idempotency and retry policy
  - stale detection when official pointers change


## Plan
1) Draft state diagrams (text form).
2) Define required timeline events per transition.
3) Link to acceptance tests to validate semantics.

## Files to read first
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- `schemas/events/envelope.schema.json`

## Files to change
- `docs/architecture/orchestration_semantics.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] QA can derive tests for WAIT/resume and stale.
- [ ] SRE can identify observability requirements from transitions.


## Completion evidence
- `docs/architecture/orchestration_semantics.md` §2 (Run and task state machines)
- `docs/architecture/orchestration_semantics.md` §3 (WAIT conditions and wakeup triggers)
- `docs/architecture/orchestration_semantics.md` §4 (Retry and idempotency policy)
- `docs/architecture/orchestration_semantics.md` §5 (Staleness semantics)

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
