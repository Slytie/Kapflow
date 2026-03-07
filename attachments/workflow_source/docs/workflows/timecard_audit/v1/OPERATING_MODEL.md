# Timecard Audit v1 - operating model

## Why this workflow exists
Timecard audit is adjacent to scheduling because dispatch actuals create the best available evidence of what happened,
but payroll export is the downstream financial system of record.

This pack reconciles the two before payroll finalization.

## Reconciliation model
Let:
- `U_d` be dispatch-derived minutes for driver `d`,
- `P_d` be payroll-export minutes for the same period.

Deterministic audit findings are functions of `(U_d, P_d)`:
- missing punch,
- hours mismatch,
- break mismatch,
- unpaid rescue / extra work.

## Boundary with payroll
The output is a corrected register and a handoff packet.
This workflow does **not** finalize payroll. `payroll.v1` remains a downstream workflow.

## Missing-input rule
Missing payroll export input must remain explicit.
The system must not assume dispatch-derived hours are automatically final payroll truth.
