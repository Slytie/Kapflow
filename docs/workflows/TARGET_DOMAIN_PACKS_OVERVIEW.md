# Target domain packs overview

This overview captures the operator-specific target decomposition confirmed from the interviews and example source artifacts.

## Workflow family split
1. `availability_request.v1`
   - Google Form time-off intake
   - manager approval / denial
   - approved availability update

2. `weekly_schedule_planning.v1`
   - Friday / pre-week Amazon route horizon intake
   - approved availability snapshot
   - actual-hours carry-forward
   - draft weekly build
   - manager review and publish
   - per-day seed materialization

3. `live_dispatch.v1`
   - daily route deltas
   - ERO / extra routes
   - no-shows / sick calls
   - issue-scoped candidate generation
   - official replan delta promotion

4. `dispatch_reporting.v1`
   - EOS upload intake
   - row-level normalization
   - >600-minute / UPD-style threshold detection
   - manager review and final reporting packet

5. `timecard_audit.v1`
   - dispatch-hours vs payroll-export reconciliation
   - deterministic mismatch detection
   - correction review
   - corrected register handoff

## Source artifact mapping
- Amazon route-update emails -> `planning.route_horizon.*` and `dispatch.route_delta_intake.*`
- Google Form time-off request -> `availability.request_submission.*`
- Scheduling spreadsheet -> `planning.approved_availability.*`
- EOS workbook / PDF -> `planning.actual_hours_snapshot.*`, `dispatch.actual_hours_snapshot.*`, and `reporting.*`
- Future payroll export -> `timecard.payroll_export.*`

## Design rules carried into the packs
- Workflow packs remain canonical.
- Hard constraints are deterministic code.
- LLM help is bounded to narrow drafting / rationale tasks.
- Official state changes occur only through approvals and pointer promotion.
- Weekly planning and day-of live dispatch are separate workflows.
- Base schedules are immutable; live operational state changes through ordered deltas.
