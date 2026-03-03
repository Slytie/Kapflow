---
id: TASK-0005
epic: EPIC-090
title: "Draft acceptance test matrix (happy path + red-team negatives)"
status: DONE
owners: ["qa"]
reviewers: ["platform", "security", "sre", "ops"]
depends_on: ["TASK-0001", "TASK-0002", "TASK-0003"]
risk: medium
---

## Context
Acceptance tests are the executable specification, especially for LLM-generated changes.

## Objective
Create `docs/planning/TEST_MATRIX.md` that maps:
- invariants → tests
- workflow stages → tests
- epics → tests

Include at minimum:
- happy path payroll
- drift after review
- degraded audit export/index
- cross-tenant and cross-domain isolation negatives
- concurrent claim semantics
- (if automation enabled) execute requires approval

## Acceptance criteria
- [ ] Ops can read and agree the scenarios reflect real operations.
- [ ] Security can point to specific tests as evidence for sign-off.
- [ ] SRE can identify required metrics/alerts from scenarios.


## Completion evidence
- `docs/planning/TEST_MATRIX.md` §1 (Invariants → required tests)
- `docs/planning/TEST_MATRIX.md` §2 (Payroll acceptance scenarios AT-PAY-001..006)
- `docs/planning/TEST_MATRIX.md` §4 (Epic → test deliverables mapping)
- `docs/planning/TEST_MATRIX.md` §5 (CI gate linkage)

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
