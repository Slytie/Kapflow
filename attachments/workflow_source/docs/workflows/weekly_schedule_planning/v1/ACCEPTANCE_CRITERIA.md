# ACCEPTANCE_CRITERIA.md - Weekly Schedule Planning v1

## Happy path
- [ ] Given a weekly Amazon route-horizon feed, an approved availability snapshot, and a recent actual-hours snapshot, the workflow can progress Stage01->Stage07 for one `PlanningWeekID`.
- [ ] Stage04 produces a draft weekly schedule plus explicit flags for WHC risk, route gaps, or fairness review.
- [ ] Stage06 approval is required before the weekly base schedule becomes official.
- [ ] Stage07 emits one or more per-service-day seed artifacts linked to the exact weekly published version.

## Critical business cases
- [ ] Friday / horizon route updates become normalized weekly route rows rather than remaining only as forwarded email text.
- [ ] The weekly draft uses actual hours from recent EOS data when forecasting WHC risk.
- [ ] Only approved availability truth affects the weekly build; raw time-off requests do not.
- [ ] Publishing the weekly base schedule does not mutate prior versions in place.

## Negative cases
- [ ] If a newer Amazon route-horizon version appears after review but before publish, drift is visible through canonical pointer drift evidence.
- [ ] If approved availability is missing for one or more required drivers, the manager review loop can request changes or more information.
- [ ] If no compliant assignment exists for one or more route slots, the workflow emits explicit flags rather than silently over-scheduling.
- [ ] If the same stage is retried, child review tasks are not duplicated.

## Domain constraints
- [ ] The official output of this pack is a weekly base schedule plus daily dispatch seeds, not a day-of replan delta.
- [ ] The pack treats Amazon route supply as exogenous input.
- [ ] Hard WHC constraints are enforced in code before any soft ranking is applied.
- [ ] Soft ranking may prefer drivers with fewer assigned shifts, on-call eligibility, or lost-work credit, but cannot override hard constraints.
