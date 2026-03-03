---
id: TASK-0024
epic: EPIC-025
title: "Define lowering contract from repo-native source to generated CompanyOS IR and pinned ExecutionSpec"
status: DONE
owners: ["platform"]
reviewers: ["security", "sre"]
depends_on: ["TASK-0020", "TASK-0021", "TASK-0022"]
risk: medium
---

## Context
The CompanyOS packet is valuable as a lowering target, but unsafe as a peer authored workflow-definition surface.

## Objective
Document generated-lowering rules and compiled artifact posture.

## Acceptance criteria
- generated CompanyOS IR is explicitly non-authoritative
- ExecutionSpec is described as compiled and pinned
