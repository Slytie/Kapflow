---
id: TASK-0023
epic: EPIC-040
title: "Define unified runtime object model for runs, tasks, execution sessions, and approvals"
status: DONE
owners: ["platform"]
reviewers: ["security", "ops", "qa"]
depends_on: ["TASK-0019", "TASK-0021"]
risk: high
---

## Context
The stage3 spike runtime had separate agent-run and human-decision concepts that could have become a second truth system.

## Objective
Define one run model, one approval model, and one event system in repo-native docs.

## Acceptance criteria
- execution session is a facet, not a peer run universe
- approvals remain a single object model with kinds
