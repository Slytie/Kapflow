# Payroll v1 - operating model (weekly pay-period close, mixed hourly and piece-rate)

## Why this workflow exists
Payroll is a governance-heavy workflow where spreadsheet convenience often hides business risk.
The workflow must:
1. transform raw time and piece-rate inputs into an attributable pay-period record,
2. surface anomalies before money movement or payslip publication,
3. bind approvals to exact reviewed versions,
4. make pay-period lock/finalize steps explicit and reconstructable.

This workflow therefore separates:
- **raw intake and triage** (Stage03-Stage04)
- **manager review and pay-period lock** (Stage05-Stage06)
- **register/finalize/output** (Stage07-Stage09)

## Problem decomposition

### 1) Gross-pay construction
At a high level, the per-worker gross-pay basis can be represented as:

\[
\text{gross\_pay}_i = h_i \cdot r_i + o_i \cdot r_i^{OT} + \sum_j q_{ij} c_j + a_i
\]

where:
- \(h_i\) = regular payable hours for worker \(i\)
- \(r_i\) = regular rate
- \(o_i\) = overtime hours
- \(r_i^{OT}\) = overtime rate or multiplier-derived equivalent
- \(q_{ij}\) = piece quantity for unit type \(j\)
- \(c_j\) = piece compensation factor for unit type \(j\)
- \(a_i\) = explicit adjustments allowed by policy

Stage 3 and 4 exist to make the inputs to this equation attributable, reviewable, and drift-visible before they become official.

### 2) Net-pay readiness
The Stage 4 slice does not implement full downstream banking integration, but it still needs a coherent pre-finalization structure:

\[
\text{net\_pay}_i = \text{gross\_pay}_i - d_i
\]

where \(d_i\) captures withholding, statutory deductions, and approved offsets represented in the run register / finalize artifacts.

The system is not the payroll law engine for every jurisdiction in Stage 4. Its job is to preserve:
- exact input provenance,
- anomaly visibility,
- approval binding,
- lock/finalize governance,
- output traceability.

## Stage interpretation

### Stage03 - Raw Time/Piece Capture
Capture and normalize source time, piece, and intake evidence without silently declaring it official beyond the staged artifact version.

### Stage04 - Timesheet Build & Triage
Build the payable working set and convert anomalies into explicit flags rather than hidden spreadsheet comments.
Typical examples:
- missing punch
- overtime anomaly
- duplicate or out-of-window piece entry
- unresolved worker master mismatch

### Stage05 - Manager Approval
The payroll manager confirms the reviewed timesheet set and either approves progression, rejects it, or requests changes.
This decision should bind to the exact reviewed artifact versions.

### Stage06 - Pre-Payroll Recon & Lock
The payroll admin confirms that the period is ready to lock.
`Lock_ID` is the explicit identifier that marks the intended pay-period lock boundary.
Lock is a governance transition, not a hidden spreadsheet status cell.

### Stage07 - Payroll Run Register
Construct the official payroll run register artifact for the locked period.
This is the key official output before finalize/payslip publication.

### Stage08 - Finance Approval & Finalize
Finance confirms the register/finalize evidence and authorizes final official outputs.
This is intentionally separate from Stage06 so lock readiness and financial finalization remain distinct decisions.

### Stage09 - Payments & Payslips
Produce the official output artifacts for payments/payslips.
Stage 4 remains artifact-first here; no bank integration is assumed.

## Roles and review model

### Core roles
- **payroll_manager** - reviews timesheet anomalies and approves progression from triage
- **payroll_admin** - performs pre-payroll reconciliation and lock review
- **finance_approver** - authorizes finalization after reviewing register/finalize evidence
- **system_worker** - background orchestration / eventing actor

### Review checkpoints
#### Manager review (Stage05)
The payroll manager should explicitly review:
- unresolved anomaly flags
- missing time or piece evidence
- overtime concentration or outlier changes versus expectation
- worker-level exceptions requiring correction before lock

#### Lock review (Stage06)
The payroll admin should explicitly review:
- `Lock_ID` readiness
- completeness of the payable population
- unresolved flags that block lock
- evidence that reviewed versions are the ones being locked/promoted

#### Finance review (Stage08)
The finance approver should explicitly review:
- register completeness
- large adjustments or reversals
- drift warnings between reviewed and promoted versions
- final output readiness

## Initial MVP defaults
These are design defaults for the reference workflow, not claims about all payroll deployments.

- Pay period is weekly and partitioned by `PayPeriodID`.
- Raw bank details must not be stored; only masked references or placeholders are allowed.
- Drift after review must remain visible rather than silently auto-resolved.
- Off-cycle corrections are out of scope for the Stage 4 slice.
- Stage 4 does not promise a jurisdiction-complete rules engine; it promises auditability, approval binding, and lock/finalize semantics.

## Conditional follow-on task loops
Even though Payroll is the linear reference workflow, review stages may still need explicit follow-on tasks.

Typical examples:
- Stage04 or Stage05 needs missing time evidence or clarification
- Stage05 manager review requests changes before lock work may continue
- Stage06 lock review needs more information before the lock boundary is accepted
- Stage08 finance review requires follow-up or sends the register back for rework

Rules:
- these are explicit child tasks, not hidden comments or spreadsheet status flips
- child tasks remain inside the same `workflow_run_id`
- retries of the same parent completion must not duplicate child tasks
- approval outcomes and child-task creation remain separate but linked pieces of truth

## Artifact principles
- Artifacts are immutable versions.
- Officialness is defined by explicit pointer promotion, not "latest file wins".
- Review and approval should bind to exact versions.
- Lock/finalize transitions should be reconstructable from events, approvals, and promoted artifacts.
- Supporting documents remain evidence, not hidden mutable state.

## Why Payroll remains in Stage 4
Payroll is no longer the primary runtime/debug wedge, but it remains strategically important because it stress-tests:
- linear approval-heavy progression,
- lock/finalize governance,
- the ability to keep generated packets downstream of official business truth.
