---
id: TASK-0003
epic: EPIC-020
title: "Define TimelineEvent envelope schema + link model (schema-first)"
status: DONE
owners: ["platform"]
reviewers: ["security", "sre", "qa"]
depends_on: ["TASK-0002"]
risk: medium
---

## Context
MVP trust level is “complete timeline + strong linking”.
Event capture must be durable and not best-effort.

## Objective
- Finalize `schemas/events/envelope.schema.json`
- Define minimal relationship link vocabulary (used_input, produced_output, approved, promoted, blocked_by, resolved_by)
- Draft degraded-mode event semantics (what event indicates exporter lag/degraded)

## Non-goals
- Do not implement exporters/indexers yet.

## Plan
1) Validate required fields for auditability + isolation.
2) Ensure schema supports idempotency/correlation.
3) Add a short `docs/architecture/event_model.md` if needed.

## Files to read
- `docs/architecture/invariants.md`
- `docs/planning/epics/EPIC-020.md`

## Files to change
- `schemas/events/envelope.schema.json`
- (optional) `docs/architecture/event_model.md`

## Acceptance criteria
- [ ] Schema is stable enough to start implementing TimelineEvent store.
- [ ] SRE can derive SLIs (freshness/backlog) from event fields.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
