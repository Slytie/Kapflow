# ACCEPTANCE_CRITERIA.md - Timecard Audit v1

## Happy path
- [ ] Dispatch-derived hours and payroll export rows are ingested for one `PayPeriodID`.
- [ ] Deterministic triage finds mismatches and creates explicit audit findings.
- [ ] Approved corrections are published into a corrected register for downstream payroll use.

## Critical business cases
- [ ] Dispatch actuals can seed the audit even before the payroll export is fully available.
- [ ] Missing punches, break mismatches, and hours mismatches are visible through flags.
- [ ] Correction review binds the human decision to the exact triage version.

## Negative cases
- [ ] Missing payroll export input remains visible rather than assumed away.
- [ ] Corrected register stays separate from payroll finalization.
- [ ] Retry or rerun does not duplicate child clarification tasks.
