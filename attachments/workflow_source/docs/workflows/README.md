# Workflow packs

Each workflow pack contains the canonical authored workflow surface for one business workflow:

- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `ACCEPTANCE_CRITERIA.md`
- `OPERATING_MODEL.md`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`

Anything else - runbook packs, tool matrices, approval logs, generated IR, one-off notebooks - is downstream.

## Current repo posture
This repo still contains the original compatibility packs:
- `schedule_planning/v1`
- `payroll/v1`

For the operator-specific rewrite, the target domain family is now expressed with separate packs:
- `weekly_schedule_planning/v1`
- `availability_request/v1`
- `live_dispatch/v1`
- `dispatch_reporting/v1`
- `timecard_audit/v1`

This reflects the confirmed split between:
1. weekly / pre-week planning,
2. per-day live dispatch,
3. end-of-day reporting,
4. approval-gated time-off / availability changes,
5. adjacent timecard audit before downstream payroll finalization.
