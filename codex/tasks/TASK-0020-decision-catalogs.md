---
id: TASK-0020
epic: EPIC-025
title: "Add canonical decision catalogs for Payroll and Schedule Planning"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa", "security"]
depends_on: ["TASK-0019"]
risk: medium
---

## Context
External runbooks and approval packets needed a canonical source for decision IDs and evidence rules.

## Objective
Add `DECISION_CATALOG.yaml` to both workflow packs.

## Source files changed
- `docs/workflows/payroll/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`

## Acceptance criteria
- both workflow packs contain canonical decision IDs
- business decisions reference stages and evidence explicitly
