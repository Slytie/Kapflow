---
id: TASK-0014
epic: EPIC-080
title: "Define required CI checks for Stage 4 (schema validate, acceptance, isolation)"
status: DONE
owners: ["sre"]
reviewers: ["platform", "security", "qa"]
depends_on: ["TASK-0002", "TASK-0003", "TASK-0005"]
risk: medium
---

## Context
To keep LLM-generated changes safe, CI must be designed as a gate for invariants.

## Objective
- Create `docs/ops/ci_required_checks.md` listing checks and what they prove.
- Define which checks are PR-required vs nightly.

## Plan
1) List checks.
2) Map each to invariant.
3) Define minimal command interface (make targets).

## Files to read first
- `docs/architecture/invariants.md`

## Files to change
- `docs/ops/ci_required_checks.md`

## Commands to run
- (doc task)

## Acceptance criteria
- [ ] Checks map to invariants.
- [ ] QA/Security/SRE agree on what is blocking.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
