---
id: TASK-0004
epic: EPIC-030
title: "Define payroll dataset_key registry and sensitivity"
status: DONE
owners: ["platform"]
reviewers: ["ops", "security", "qa"]
depends_on: ["TASK-0001"]
risk: low
---

## Context
The dataset registry prevents invented keys and clarifies sensitivity/retention.

## Objective
- Finalize `schemas/artifacts/dataset_keys.yaml` based on the template pack.
- Confirm which artifacts are official_input vs official_output vs evidence.

## Non-goals
- Do not set final retention rules (future).

## Acceptance criteria
- [ ] Dataset keys cover Stage01..Stage09 artifacts used in MVP slice.
- [ ] Sensitivity is assigned (internal/confidential) to support future policy decisions.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
