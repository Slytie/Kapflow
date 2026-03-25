# Logistics workpages v0 - product brief

## Purpose
This brief distills the current product intent for the first logistics workpages into repo-native source so fresh-session Codex runs do not depend on external attachments.

A **workpage** in this tranche is:
- a full-page operator-facing UI,
- derived from normalized logistics data,
- easier to use than the raw spreadsheet/report,
- and still subordinate to the repo's artifact-first authority model.

In v0, the first workpages are **frontend-first prototypes**. They are not yet generic artifact editors and they are not yet backed by a canonical workpage API.

## Users and posture
Primary users:
- dispatcher
- operations manager
- schedule planner

Not in scope for v0:
- driver login / self-service portal
- general spreadsheet editing in-browser
- exact Excel reproduction
- PDF generation as the primary output
- a live-dispatch morning control tower as a first surface

## Source-material distillation
This brief is grounded in:
- the current repo logistics workflow family (`weekly_schedule_planning.v1`, `live_dispatch.v1`, `dispatch_reporting.v1`),
- repo-native normalized example YAMLs for weekly scheduling and dispatch reporting,
- an uploaded EOS example PDF,
- and an uploaded CEO transcript describing the intended operator workflow.

The external materials converge on one product stance:
- the UI should feel like a **form + history + operations summary**,
- not like a generic spreadsheet clone,
- and not like a heavyweight dispatch suite in the first cut.

The CEO transcript also sharpens the scope boundary:
- **schedule** is the first thing to get right,
- the interface should stay close to the current human workflow,
- the end-of-day surface is "really just a form" plus history and management visibility,
- and any day-of replan assistance should remain subordinate to the weekly schedule page rather than turning the first tranche into a live-dispatch console.

## Schedule workpage v0
### What problem it solves
The first schedule page should help management/scheduling review the **weekly plan** with enough selected-day context to make better decisions and spot historical patterns.

### User-facing outcome
The operator should be able to:
- look at the current planning week quickly,
- understand daily route demand and coverage posture,
- inspect driver availability / preferred schedule / restrictions,
- see relevant recent history,
- preview the currently selected service day,
- and perform a small number of **local what-if adjustments** without entering a raw spreadsheet.

### Core UI sections
1. **Week summary**
   - planning week
   - station / service area
   - required route totals
   - on-call target
   - excess-capacity target
   - notable warnings / planner notes

2. **Daily demand and selected-day preview**
   - one row per service day for v0, with demand and coverage posture
   - one selected-day preview area showing the operational context for that day
   - this is still a weekly-planning page, not a live-dispatch command surface

3. **Driver roster / detail**
   - driver name
   - employment type
   - preferred slot class
   - target shifts per week
   - on-call eligibility
   - recent actual-hours / previous-week context

4. **Selected-day what-if inputs**
   - local/demo-scoped inputs such as scenario sick calls, extra routes, or on-call choices
   - these are present to validate the page contract and operator workflow, not to claim ownership of day-of dispatch truth in v0

5. **History stub**
   - recent-week summaries or prior-week metrics
   - visible in v0 even if minimally interactive

### Important product constraints
- Keep it simple. The first page is about **weekly planning review + selected-day preview**, not the full live-dispatch morning process.
- Do not emulate Excel cell layout.
- Do not start from the legacy schedule-only FE routes.
- Build it as a full page, not a drawer.
- Any day-of adjustment affordance in v0 must be framed as **local what-if input**, not as semantically authoritative live-dispatch editing.

## End-of-day report workpage v0
### What problem it solves
Dispatch closes out the day with a mix of uploaded operational files and manual entry. The first EOD page should consolidate that into a guided workflow and a reusable daily history surface.

### User-facing outcome
The operator should be able to:
- review route-level actuals that were pulled from the EOS material,
- enter a small amount of manual information already collected today,
- review UPD / `>600 minute` candidates,
- capture rescues / incidents / notes,
- save a consistent daily reporting draft,
- and later review history by day/week/month.

### Workflow anchor
The v0 EOD page should be thought of as a **draft/review reporting surface**, not the final official packet.

For future backend integration, the closest dataset anchor is:
- `reporting.upd_draft.workbook`

not:
- `reporting.final_packet.workbook`

That keeps the page aligned with the actual reporting workflow stages:
- Stage02 normalized actuals
- Stage03 threshold detection + draft packet
- Stage04 manager review
- Stage05 final packet later

### Core UI sections
1. **Top summary cards**
   - routes
   - packages dispatched / delivered / returned
   - delivered % / return %
   - average actual route time
   - estimated overtime / `>600` warnings
   - formula-integrity warning if the source workbook was broken

2. **Route actuals table**
   - route
   - driver
   - packages dispatched / delivered
   - planned start/finish
   - actual start/finish
   - actual minutes
   - returns / reasons
   - UPD candidate marker

3. **Manual closeout form**
   - sick calls / unavailable drivers
   - working devices / key status
   - rescues
   - incidents
   - last driver clock-out
   - dispatcher / manager notes

4. **UPD candidate checklist**
   - `>600 minute` candidates
   - reason
   - manager note / confirmation affordance

5. **History stub**
   - prior daily reports
   - weekly/monthly summary entrypoint later

### Important product constraints
- This should feel like a **guided operational form**, not a raw workbook.
- The row-level actuals are more trustworthy than fragile spreadsheet summary formulas.
- Do not attempt to reproduce every summary formula from the source workbook in the first cut.
- In the first FE tranche, use a **consistent repo-native example pack** for the page. Do not mix one day's summary values with another day's row examples.

## Artifact authority boundary
Long term, a workpage should be connected to an artifact version and submit into a new artifact version.

For v0 FE work, the correct boundary is narrower:
- use normalized examples + repo-native view-model fixtures first,
- stabilize the page contract and UX,
- and only then add backend projection/submit contracts.

## Non-goals for the first build package
- no generic artifact-linked workpage runtime yet
- no `GET /api/v1/workpages/*` contract yet
- no backend workbook extraction/materialization yet
- no live-dispatch morning page yet
- no PDF-centric rendering or export work
- no permission model expansion beyond current logistics operator roles
