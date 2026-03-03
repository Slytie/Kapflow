---
id: TASK-0007
epic: EPIC-020
title: "Define degraded-mode signals, metrics, and alert thresholds"
status: DONE
owners: ["sre"]
reviewers: ["platform", "security"]
depends_on: ["TASK-0003"]
risk: medium
---

## Context
Fail-open semantics require a clear definition of degraded audit visibility, and SRE must be able to alert on it.

## Objective
- Create `docs/ops/degraded_mode.md` defining signals/metrics.
- Add initial SLO hypotheses for timeline freshness and outbox lag.

## Plan
1) Define what counts as degraded: exporter backlog age/size thresholds.
2) Define required metrics names.
3) Define alert rules (placeholder thresholds).

## Files to read first
- `docs/architecture/invariants.md`
- `docs/planning/checklists/SRE_SIGNOFF.md`

## Files to change
- `docs/ops/degraded_mode.md`
- (optional) update SRE checklist

## Commands to run
- (doc task; no commands yet)

## Acceptance criteria
- [ ] Degraded-mode definition is unambiguous.
- [ ] SRE can derive dashboard+alert requirements from the doc.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
