---
id: TASK-0025
epic: EPIC-025
title: "Add refinement and generated-artifact check requirements to planning and ops docs"
status: DONE
owners: ["sre", "platform"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0022", "TASK-0024"]
risk: medium
---

## Context
Without explicit refinement and freshness checks, the merger would remain conceptual only.

## Objective
Add CI, test-matrix, and runbook guidance for source-to-generated consistency.

## Acceptance criteria
- test matrix covers no-shadow-truth checks
- CI required checks include generated freshness and refinement checks
