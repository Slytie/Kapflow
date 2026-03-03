---
id: TASK-0012
epic: EPIC-060
title: "Specify approval object model and server-side enforcement points"
status: DONE
owners: ["platform", "security"]
reviewers: ["ops", "qa"]
depends_on: ["TASK-0001", "TASK-0002", "TASK-0009"]
risk: high
---

## Context
Approvals must not be UI-only. We need the approval model and enforcement points specified before coding.

## Objective
- Create `docs/architecture/approval_model.md` covering:
  - approval request/grant objects
  - links to artifact versions and promotions
  - required timeline events
  - enforcement rules (server-side)


## Plan
1) Define minimal approval types for payroll stages.
2) Define required metadata.
3) Define enforcement gates for promote/lock/finalize.

## Files to read first
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`

## Files to change
- `docs/architecture/approval_model.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Security agrees enforcement is server-side.
- [ ] Ops agrees metadata is sufficient.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
