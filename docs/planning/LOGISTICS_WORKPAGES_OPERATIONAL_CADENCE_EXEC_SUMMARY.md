# Logistics Workpages - operational demo executive summary

Status note (2026-04-06):
- EPIC-125 is complete.
- This document now serves as historical planning rationale for the first operator-loop tranche.
- The later feedback-consuming follow-on work is already reflected in completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches.

## Purpose
Move from **proven workpage technology** to a **running first-user operator lane** that can be demoed locally, then run continuously in a small production-shaped environment, before the hardening epic.

The historical recommended sequence was:

\[
\text{EPIC-124 (stage-linked workpages)} \,\to\, \text{EPIC-125 (operational cadence demo)} \,\to\, \text{EPIC-126 (hardening/closeout)}
\]

## Target first use case
The first use case should prove three connected operational loops:

### Weekly Friday planning loop
\[
I^{weekly}_{stage04-ready} \to B^{stage04}_{schedule} \to R^{manager}_{schedule} \to O^{weekly}_{published}
\]

where:
- \(I^{weekly}_{stage04-ready}\) = the authoritative Friday planning inputs required to run the existing Stage04 schedule-build lane,
- \(B^{stage04}_{schedule}\) = the bounded Stage04 planner/agent build,
- \(R^{manager}_{schedule}\) = review/edit of the draft weekly schedule through the existing workpage,
- \(O^{weekly}_{published}\) = the official published weekly schedule workbook.

### Minimal daily manual replan loop
\[
S_d \oplus \Delta^{manual}_d \to O^{dispatch}_d
\]

where:
- \(S_d\) = the immutable daily seed emitted from weekly planning,
- \(\Delta^{manual}_d\) = a manual route-delta intake for the service day,
- \(O^{dispatch}_d\) = the official promoted daily replan delta.

This loop is intentionally **non-algorithmic** in v1. It proves that the daily schedule can be changed each day without widening into live-dispatch candidate generation.

### Daily reporting closeout loop
\[
I^{daily}_{eos} \to B^{reporting}_{draft} \to R^{manager}_{eod} \to O^{daily}_{final} \to H_{daily \to weekly}
\]

where:
- \(I^{daily}_{eos}\) = the daily EOS/actual-routes upload,
- \(B^{reporting}_{draft}\) = workflow-native generation of the draft reporting artifact,
- \(R^{manager}_{eod}\) = review of that generated artifact through the existing EOD workpage,
- \(O^{daily}_{final}\) = the official finalized reporting workbook,
- \(H_{daily \to weekly}\) = the existing reporting-to-planning actual-hours feedback used for compliance in future planning.

## Repo-grounded recommendation
### Keep the first operator lane to three workflow families only
- `weekly_schedule_planning.v1`
- `live_dispatch.v1` (manual delta lane only)
- `dispatch_reporting.v1`

### Do **not** make raw email authoritative yet
For the first running demo:
- keep the raw routes email/doc as **evidence**,
- keep the operator-facing machine-truth weekly intake as **structured workbook input**.

The red-team review changed the prior plan here. Requiring a Stage01 route-email/horizon parser before the first running loop would add unnecessary risk.

### Do **not** add a generic scheduler
Use an **external idempotent CLI cadence tick** invoked by cron/systemd/Kubernetes CronJob.

### Do **not** widen live dispatch into algorithmic candidate generation
The first production-shaped loop only needs a bounded **manual daily delta lane**.

## Key architectural decisions
1. **Weekly Friday authoritative input should be Stage04-ready.**
   For the first running demo, the required operator upload should be the workbook the existing weekly Stage04 lane actually needs (for example `planning.route_slot_requirements.workbook`, plus approved availability and a stable driver-capabilities baseline), while route-horizon email/doc remains evidence.

2. **Daily actual-routes intake should stay inside `dispatch_reporting.v1`.**
   The raw EOS workbook is already the right authoritative input, and the repo already treats row-level actuals as truth over fragile formulas.

3. **Use the existing finalized reporting handoff for compliance truth.**
   Actual routes taken should continue to drive future planning compliance through `planning.actual_hours_snapshot.workbook`. The minimal daily live-dispatch lane can reuse the supported actual-hours snapshot kinds instead of introducing a second handoff.

4. **Include a minimal manual daily replan loop now.**
   This satisfies the need for day-of schedule changes without taking on live-dispatch candidate generation or a new workpage surface.

5. **Local demo comes before continuous production-shaped cadence.**
   Expect heavy feedback after the first local demo. The plan therefore separates:
   - a **local operator demo milestone**,
   - from the later **continuous production-shaped cadence** milestone.

## What changed after red-team review
### A. Excluding live dispatch entirely is too narrow
The product requirement now clearly includes a daily schedule-change capability, so the first operator lane must include a minimal manual live-dispatch slice.

### B. Building a weekly Stage01->Stage04 normalization bridge is not the smartest first move
The repo already has a working Stage04 planning lane. Requiring Stage04-ready workbook inputs for the first running demo is lower risk than trying to add a route-email normalization pipeline immediately.

### C. The first local demo should happen before cadence automation is complete
This is the best time to absorb UI/operator feedback.

### D. The reporting workpage remains the first and most important review workpage in the operational demo
The user specifically wants a workpage attached to the artifact generated from daily dispatch closeout for review. That stays central in the plan.

## Risks
1. **Weekly authoritative-input policy may still be underspecified.**
   The exact minimum required Friday inputs must be frozen carefully so the Stage04 lane can run truthfully.
2. **Manual daily replan scope could drift into live-dispatch algorithmics.**
   The stop line must remain explicit: manual delta only.
3. **Reporting finalization and compliance handoff could be treated as optional.**
   They are not optional if actual routes taken are supposed to inform compliance truth.
4. **The first local demo may surface substantial UX and operator-language issues.**
   That feedback was later consumed by completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches rather than reopening EPIC-125 indefinitely.
5. **Schedule draft artifacts remain partially JSON-backed today.**
   This remains acceptable technical debt for the first running lane, but must stay explicit.

## Historical milestone timing
### Historical local FE/BE demo and UI user-testing handoff
At planning time, the repo was meant to start **as soon as EPIC-125 reached the local-demo milestone** (the task that adds the local runbook, seeded operator smoke path, and demo entrypoints).

That is the right point to:
- run the backend and frontend locally,
- walk the weekly planning lane,
- walk the daily reporting lane,
- and gather high-volume UI/operator feedback.

### Historical production-shaped continuous demo handoff
The repo was meant to move to the first continuously running environment only after the later EPIC-125 cadence/deployment milestone landed:
- external cadence tick,
- single-node deploy/runbook,
- operational smoke path.

### Historical hardening handoff
At planning time, EPIC-126 hardening was intentionally deferred until after local demo feedback had been gathered.
