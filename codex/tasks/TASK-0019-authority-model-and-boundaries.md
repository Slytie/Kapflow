---
id: TASK-0019
epic: EPIC-015
title: "Freeze authority model and source-of-truth boundaries"
status: DONE
owners: ["platform"]
reviewers: ["security", "ops", "qa"]
depends_on: ["TASK-0001", "TASK-0016"]
risk: high
---

## Context
The merger risk was dual authorship of workflow semantics and confusion about what is authoritative.

## Objective
Add a repo-native authority model that makes the single truth system explicit.

## Source files to read first
- `docs/architecture/AGENTIC_LAYER_AND_MERGE_REVIEW.md`
- `docs/vision/PROJECT_VISION.md`
- `Repo_RFC_Codex_Ready_v0_3.md`

## Source files changed
- `docs/architecture/AUTHORITY_MODEL.md`
- `README.md`
- `AGENTS.md`
- `docs/index.md`

## Acceptance criteria
- one authority chain is explicit
- no core read-path doc implies a second peer truth system

## Notes / decisions
Completed in the merger update that introduced repo-native authority docs.
