> Document classification: descriptive logistics current-state source. See `docs/domains/logistics/DOC_INVENTORY.yaml`.

# LOGISTICS_WORKPAGES_V1_OPERATOR_READINESS_NOTE.md

## Purpose
Summarize the frozen Workpages v1 operator boundary after EPIC-131 closeout.

## Final v1 posture
- `schedule-v0` is the weekly reassignment/on-call editor plus server recalculation surface.
- `route-demand-v0` is the route-demand truth editor.
- `driver-preferences-v0` is the soft/advisory weekly snapshot editor.
- `eod-v0` remains the dispatch-reporting draft/review surface over immutable workbook artifacts.

## Navigation rules
- Accepted history and draft lineage are separate.
- Accepted arrows navigate accepted schedule history only.
- Draft rails navigate draft lineage only.

## Route posture
- Frontend workpage routes are canonical-only under `/runs/:workflowRunId/workpages/*`.
- Backend workpage APIs are canonical-only under `/api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}*`.
- `/demo/logistics` remains the shell entrypoint only; it does not host nested demo workpage pages.

## Explicit non-v1 deferrals
- date-specific driver exceptions
- automatic route-demand-triggered rescheduling
- broader feedback-driven hardening beyond EPIC-126 cleanup
