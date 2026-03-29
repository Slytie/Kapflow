# Logistics Workpages - operational cadence plan (red-team revised)

## Goal
Deliver the smallest truthful operator lane that proves Workpages can run the first real logistics use case end to end:
- weekly Friday planning,
- bounded manual day-of schedule change,
- daily dispatch closeout and feedback into compliance truth.

## Repo-grounded findings
### 1) The weekly Stage04 planning lane already exists and is valuable
The repo already has:
- weekly planning workflow semantics,
- a bounded Stage04 planner/agent lane,
- schedule draft workpage review/editing,
- schedule publish semantics in the workflow contract.

The smartest near-term move is to **feed this lane truthfully**, not replace it.

### 2) Dispatch reporting is already the right home for actual-routes truth
The repo already has:
- EOS intake,
- row-normalization semantics,
- draft reporting packet semantics,
- manager review/final packet semantics,
- a reporting->planning actual-hours feedback lane.

So the daily review workpage should remain attached to the generated reporting draft artifact.

### 3) Live dispatch already has the right authority model for manual day-of change
The repo already has:
- weekly->live seed handoff,
- lazy live-dispatch run activation,
- route-delta intake artifacts,
- official replan-delta promotion semantics,
- explicit ordered-delta officialness.

That means the minimum daily schedule-change capability should be implemented as a **manual live-dispatch delta lane**, not by widening the weekly schedule workpage.

### 4) The previous plan overreached on weekly normalization
A full Stage01 route-horizon/email -> Stage04 bridge would add unnecessary risk before the first operator demo.

For the first running lane, the better decision is:
- require Stage04-ready structured weekly inputs,
- preserve raw route email/doc as evidence,
- defer upstream normalization/parser work.

### 5) A local demo milestone should come before external cadence automation
Best practice at this stage is:
- get the first local weekly+daily loop running,
- demo the UI and collect operator feedback,
- then wire the continuous external cadence and deployment path,
- then harden.

## Recommended epic sequence
### EPIC-125 — Operational cadence demo
Build the first local and production-shaped operator loop.

### EPIC-126 — Workpages v1 hardening and closeout
Consume feedback, harden the operator lane, tighten route truth, and close the v1 boundary.

## EPIC-125 architecture
### Weekly planning lane
For the first operator loop, treat these as the authoritative weekly inputs:
- `planning.route_slot_requirements.workbook` (required)
- `planning.approved_availability.workbook` (required)
- `planning.driver_capabilities.workbook` (seeded baseline; update only if truly needed)
- `planning.route_horizon.doc` / route email / horizon workbook as evidence or optional upstream reference
- `planning.actual_hours_snapshot.workbook` from finalized reporting feedback

Then:
\[
I^{weekly}_{stage04-ready} \to Stage04 \to \text{schedule review workpage} \to published\_weekly\_schedule
\]

### Daily reporting lane
Use:
- `reporting.eos_raw.workbook` as the authoritative daily intake,
- generate `reporting.upd_draft.workbook`,
- review it through the existing EOD artifact-backed workpage,
- finalize to `reporting.final_packet.workbook`,
- hand off actual-hours truth to weekly planning.

### Minimal daily replan lane
Use:
- `planning.daily_dispatch_seed.workbook` from weekly Stage07 handoff,
- `dispatch.route_delta_intake.workbook` as the authoritative manual day-of delta input,
- the existing live-dispatch activation / official delta promotion semantics,
- **no algorithmic candidate generation**,
- **no live-dispatch workpage in this epic unless the repo already supports it trivially**.

This yields:
\[
base\_seed_d \oplus manual\_delta_d \to official\_replan\_delta_d
\]

## Why this is the most intelligent minimal-change path
It reuses:
- existing workflow families,
- existing artifact kinds,
- existing handoff runtime,
- existing workpages,
- existing pointer/officialness semantics,
- existing schedule and reporting review surfaces.

It avoids introducing, for now:
- email ingestion/parsing as system truth,
- a generic scheduler,
- live-dispatch algorithmic candidate generation,
- a broader schedule-control UI,
- a new route family or shell.

## Local-demo milestone
The first local demo should happen once the repo can truthfully do all of the following on a single developer machine:
1. seed or create the next weekly planning run,
2. upload the required weekly planning inputs,
3. run the existing Stage04 planner/agent,
4. review/edit the draft schedule in the workpage,
5. publish the schedule,
6. seed a live-dispatch service day,
7. upload a manual daily route delta and produce an official replan delta,
8. upload EOS raw,
9. review the generated reporting draft in the EOD workpage,
10. finalize the daily reporting packet,
11. verify the actual-hours feedback appears in planning truth.

This milestone should come **before** external cadence automation.

## Production-shaped milestone
Only after the local milestone is working should the repo add:
- an idempotent cadence CLI tick,
- cron/systemd/Kubernetes CronJob wiring,
- a single-node deployment/runbook,
- an operator smoke path for the continuous environment.

## EPIC-125 stop lines
Do not include:
- live-dispatch candidate generation or ranking,
- a live-dispatch workpage unless it is near-trivial and clearly bounded,
- Stage06/Stage07 schedule workpage widening,
- raw route-email parser ownership,
- broad hardening work,
- multi-node operational complexity.

## EPIC-126 goal
Once the first local demo has happened and the production-shaped demo environment is up, EPIC-126 should:
- absorb feedback,
- harden UX and operator language,
- strengthen regression and observability,
- clean up route/alias truth,
- define the explicit Workpages v1 closure boundary.
