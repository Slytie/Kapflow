# ACCEPTANCE_CRITERIA.md — Payroll v1 (Stage 4)

These criteria are intended to become the Stage 4 acceptance suite (S4-A07).

## Happy path (minimum)
- [ ] Given PayPeriodID PP-YYYY-Www and scope (tenant, domain),
      when official inputs are promoted,
      then a payroll workflow run can progress Stage03→Stage09 to completion.
- [ ] Timeline contains a complete sequence of events with strong links:
      run_id, task_ids, approval_ids, artifact_version_ids, and pointer promotions.
- [ ] If a completed task causes rework, more-information gathering, or final review, the child task run is emitted explicitly rather than hidden in mutable task state.

## Core negative cases (must pass)
### AC-1 Loose promotion records exact version
- [ ] Approve & Promote Latest promotes the current latest eligible artifact version
- [ ] Timeline records `promoted_artifact_version_id`

### AC-2 Drift after review is visible
- [ ] If a newer version exists at time-of-promotion than the version reviewed,
      then emit `artifact.pointer.drift_detected` (or equivalent)
      and surface it in timeline/UI.

### AC-3 Fail-open exporters (degraded audit visibility)
- [ ] If export/index is down,
      then state transitions still succeed AND authoritative timeline events still exist.
- [ ] Degraded mode is visible and alertable.

### AC-4 Domain partition enforcement
- [ ] Cross-tenant and cross-domain reads/writes are denied and logged.
- [ ] Background consumers enforce the same rules (exports, indexers, workers).

## Payroll-specific constraints (from template pack)
- [ ] Do not store raw bank account numbers; store masked references only.
- [ ] Lock stage records Lock_ID and approval metadata (who/when/method).



## Overlay consistency
- [ ] Decision catalog references only valid stage IDs and actions for this workflow.
- [ ] Execution profile references only valid stage IDs and required evidence keys for this workflow.
- [ ] Any generated runbook or CompanyOS IR derived from this pack does not invent official outputs or approvals outside the canonical files.
