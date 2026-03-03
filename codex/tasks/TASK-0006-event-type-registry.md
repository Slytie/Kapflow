---
id: TASK-0006
epic: EPIC-020
title: "Create event-type registry and required fields per event"
status: DONE
owners: ["platform"]
reviewers: ["security", "qa", "sre"]
depends_on: ["TASK-0003"]
risk: medium
---

## Context
We need a stable set of event types for the payroll slice so implementation and acceptance tests do not invent names.

## Objective
- Create `schemas/events/event_type_registry.yaml` listing event types and required links/fields.
- Ensure alignment with `WORKFLOW_CONTRACT.yaml` required_events.

## Plan
1) Enumerate event types used in payroll slice.
2) For each event type, define required `links` relationships.
3) Add notes about idempotency keys and correlation fields.

## Files to read first
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- `schemas/events/envelope.schema.json`

## Files to change
- `schemas/events/event_type_registry.yaml`
- (optional) update contract required_events if needed

## Commands to run
- (doc/schema task; no commands yet)

## Acceptance criteria
- [ ] Event type registry exists and is reviewed.
- [ ] Required fields/links are explicit for each event type.


## Completion evidence
- `schemas/events/event_type_registry.yaml` (event types + required links)
- `docs/workflows/*/v1/WORKFLOW_CONTRACT.yaml` `required_events` lists (aligned vocabulary)

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
