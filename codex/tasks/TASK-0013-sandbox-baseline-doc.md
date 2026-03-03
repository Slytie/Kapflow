---
id: TASK-0013
epic: EPIC-070
title: "Define minimum sandbox posture for tool execution (MVP baseline)"
status: DONE
owners: ["security"]
reviewers: ["sre", "platform"]
depends_on: ["TASK-0012"]
risk: high
---

## Context
Stage 4 security gate requires minimum sandbox posture for any automation/tool execution.

## Objective
- Create `docs/security/sandbox-and-approvals.md` defining:
  - execute requires approval
  - default-deny egress
  - resource/output limits
  - provenance logging
  - secrets handling (no long-lived creds)


## Plan
1) Write baseline constraints.
2) Define evidence required for security sign-off.
3) Link to acceptance tests.

## Files to read first
- `docs/planning/checklists/SECURITY_SIGNOFF.md`

## Files to change
- `docs/security/sandbox-and-approvals.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Security checklist aligns with sandbox doc.
- [ ] Baseline is testable and auditable.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
