# EPIC-000 - Payroll workflow contract v1 (freeze)

## Summary
Freeze the Payroll workflow family as a linear approval-heavy reference workflow and governance benchmark.

## Why this epic exists (risk retired)
Provides the secondary business contract used to verify that the platform remains valid for lock/finalize-heavy flows even while Schedule Planning is the primary runtime/debug wedge.

## Scope
### In scope
- canonical workflow contract
- artifact map
- acceptance criteria
- operating model
- alignment with decision catalog and execution profile

### Out of scope
- downstream generated runbook pack as source of truth

## Dependencies
- -

## Key decisions / constraints
- must obey `docs/architecture/invariants.md`
- must remain the authoritative business definition for Payroll
- downstream execution overlay may refine but not broaden it

## Deliverables
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/payroll/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/payroll/v1/ACCEPTANCE_CRITERIA.md`
- `docs/workflows/payroll/v1/OPERATING_MODEL.md`

## Definition of Done
- Payroll business semantics are stable enough to validate shared runtime/approval semantics against a governance-heavy linear flow

## Tasks
- TASK-0001
