# ACCEPTANCE_CRITERIA.md - Availability Request v1

## Happy path
- [ ] A Google Form request is normalized into canonical request artifacts.
- [ ] A manager decision is recorded through the approval boundary.
- [ ] Only an approved or partially approved decision updates the official availability plan.

## Critical business cases
- [ ] Request intake captures name, unavailable weekdays, requested dates, reason, and typed signature.
- [ ] Peak / blackout / short-notice policy hints are visible to the reviewer.
- [ ] The updated approved availability can trigger downstream weekly replanning or live dispatch when affected dates are already published.

## Negative cases
- [ ] Raw submission never directly changes scheduling truth.
- [ ] Denied requests preserve existing availability.
- [ ] Partial approvals record both approved and denied dates explicitly.
- [ ] Needs-information cases remain pending until clarified.
