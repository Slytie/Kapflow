# CURRENT_FOCUS.md

## Stage
Stage 4 - Vertical Slice MVP (repo merged around one truth system)

## Current milestone
Primary runtime/debug work remains the logistics weekly/live family. EPIC-131, the EPIC-126 Workpages v1 cleanup trio, and EPIC-132 are complete, and the public Workpages v1 posture is now canonical-only:
- frontend workpage routes live under `/runs/:workflowRunId/workpages/*`
- backend workpage APIs live under `/api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}*`
- `/demo/logistics` remains the shell entrypoint, but nested demo workpage routes are retired

The just-completed workpage settlement closeout now leaves the repo with:
- a dedicated backend mutation lane via `make PYTHON=python3.11 workpage-mutation-smoke`
- a dedicated frontend workpage lane via `make frontend-workpages-smoke`
- supported-environment verification truth anchored to Python `3.11` and Node `20` clean installs

The just-completed app-facing workpage tranche is **EPIC-133 - Workpage fragility reduction and extensibility hardening**:
- backend-owned lineage/latest-draft/history seams are complete for canonical workpage pages
- server-authored action execution is complete for canonical create/submit flows
- `/demo/logistics` is now a launcher-only shell that hands off to canonical workpage/workspace routes
- the former concentration files now resolve through thinner facades and explicit source-budget guardrails

There is no new app-facing product-expansion epic selected after EPIC-133 closeout. EPIC-134 is the active demo-enablement tranche for the already-landed canonical workpage surfaces:
- `TASK-0221` - freeze the minimal demo boundary, canonical-route posture, and no-new-demo-mode rule
- `TASK-0222` - correct the weekly-first local demo smoke diagnosis and reporting-intake runtime-dependency truth
- `TASK-0223` - add a one-command canonical workpage demo-prep script
- `TASK-0224` - add the demo runbook and a canonical workpage demo-prep regression

EPIC-126 remains completed cleanup history, but it is no longer the active post-EPIC-131 plan.

## Current implemented baseline
- weekly schedule landing, artifact editor, live preview, pinned dependency baselines, accepted-series navigation, and draft-lineage navigation on canonical schedule routes
- `route-demand-v0` run landing plus artifact-backed immutable day-count editor
- `driver-preferences-v0` run landing, snapshot creation, artifact-backed editor/history, and soft advisory schedule integration
- `eod-v0` run landing plus canonical artifact-backed immutable workbook editing
- backend workspace workpage actions with active vocabulary `open_route | create_then_open`
- backend-owned frontend snapshots for canonical schedule, route-demand, driver-preferences, EOD, workspace, board, run-detail, timeline, and official-output surfaces

Canonical workpage routes now in active use:
- frontend:
  - `/runs/:workflowRunId/workpages/schedule-v0`
  - `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/route-demand-v0`
  - `/runs/:workflowRunId/workpages/route-demand-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/driver-preferences-v0`
  - `/runs/:workflowRunId/workpages/driver-preferences-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/eod-v0`
  - `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`
- backend:
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}`
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}/artifacts/{artifact_version_id}`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}/artifacts/{artifact_version_id}/submit`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/artifacts/{artifact_version_id}/preview`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0/snapshots`

Frozen product boundary:
- `schedule-v0` = reassignment/on-call edits plus recalculation only
- `route-demand-v0` = route-demand truth editor
- `driver-preferences-v0` = soft/advisory weekly snapshot
- accepted history and draft lineage remain separate

Still deferred beyond the completed Workpages v1 + EPIC-133 hardening tranche:
- date-specific driver exceptions
- automatic agentic rescheduling after route-demand changes
- broader feedback-driven hardening beyond the settlement tranche

## Available broader backlog (after EPIC-134)
1. `TASK-0154` - Finish the remaining bounded live-dispatch closure around the manual daily-replan lane.
2. `TASK-0156` - Add the external cadence tick and single-node production-shaped runbook.
3. `TASK-0157` - Capture post-demo feedback against the canonical Workpages v1 posture.

## Test-first working mode
Before adding runtime services or API surfaces:
1. update authoritative docs / schemas / traces,
2. update the scenario catalog and pytest oracles,
3. then implement runtime code.

Default verification loop:
- `make assurance-fast`
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make security`
