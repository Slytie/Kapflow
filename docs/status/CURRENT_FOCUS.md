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

The just-completed demo-enablement tranche is **EPIC-134 - Minimal canonical workpage demo enablement**:
- supported-environment truth is corrected for the weekly-first local demo smoke and reporting-intake dependency classification
- `scripts/run_logistics_workpage_demo_prep.py` provides a deterministic, idempotent canonical workpage prep path with machine-readable route output
- `docs/ops/runbooks/logistics_canonical_workpage_demo.md` now documents the supported canonical workpage walkthrough without requiring OpenAI
- prep-script regressions and docs-as-truth guardrails now cover the canonical route walkthrough and runbook discoverability

The just-completed production-shaped cadence milestone is **TASK-0156 - External cadence tick and single-node logistics operator runbook**:
- `onetruthctl cadence tick-logistics` now ensures due weekly/reporting state and prepares live dispatch once weekly publish truth exists
- `docs/ops/runbooks/logistics_single_node_cadence.md` documents the bounded continuous single-node operator posture over the existing release/deploy topology

The current demo-facing weekly-planning enhancement is the landed **route-demand week-by-week activation plus existing-week coverage** slice:
- `route-demand-v0` now shows one editable operational week at a time
- `Add a week` creates or reopens the real next weekly run and seeds an empty future-week route-demand artifact there
- future-week `Save and run scheduling agent` remains the explicit greenfield scheduling trigger from route demand
- the shared route-demand editor now lets operators edit both planned route counts and on-call targets in the popup and full-page artifact view
- future-week scheduling activation now treats positive on-call target demand the same as positive route demand, while existing-week coverage remains route-increase-only
- existing-week positive route-count increases can use `Run coverage agent` to save or reuse successor route-demand truth, then hand off into the canonical `schedule-v0` quick-edit popup with backend-ranked coverage recommendations
- plain route-demand save no longer spawns the legacy refresh task
- successful future-week scheduling activation still hands off to the canonical `schedule-v0` route and reuses the existing quick-edit popup entrypoint
- successful existing-week coverage apply stays in the pre-publish weekly-draft lane and creates the successor `planning.draft_weekly_schedule.workbook` draft only from the backend coverage-apply path

The current dispatch-reporting operator enhancement is the landed **service-date-selectable route-activity upload** slice:
- the `Upload route activity` popup now lets operators pick the reporting service date after choosing the workbook
- the selected service date is authoritative upload metadata, ahead of filename-derived dates
- when the selected date differs from the current EOD run, the popup resolves or creates the matching `dispatch_reporting.v1` run and continues closeout there

EPIC-125 is now completed history:
- `TASK-0154` is reconciled to `DONE` from the already-landed live-dispatch delta lane exercised by runtime handlers, the local demo smoke, and the operator runbooks
- `TASK-0157` records the first-demo feedback handoff in `docs/planning/LOGISTICS_WORKPAGES_EPIC125_CLOSEOUT_AND_FEEDBACK_NOTE.md`
- no EPIC-125 carry-forward task remains open

EPIC-126 remains completed cleanup history, but it is no longer the active post-EPIC-131 plan.

## Current implemented baseline
- weekly schedule landing, artifact editor, live preview, pinned dependency baselines, backend-authored accepted/draft lineage metadata, and backend-ranked route-demand coverage handoff on canonical schedule routes
- `route-demand-v0` run landing plus artifact-backed immutable day-count editor with next-week activation, existing-week coverage handoff, and explicit save-and-run scheduling paths
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

Still deferred beyond the currently implemented baseline:
- contact-data authoring surfaces
- generalized live-dispatch workpage productization beyond the shared schedule popup
- broader feedback-driven operator hardening beyond the current bounded pre-publish route-demand activation and coverage slice

## Available broader backlog (after EPIC-134)
No EPIC-125 carry-forward backlog item remains open.
Future app-facing product expansion after this landed route-demand slice should still be selected deliberately from later feedback and deferred items, not implied by stale task state.

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

## CAPEX v6 imported planning backlog
- CAPEX v6 is imported as gated planning backlog only: `TASK-0233` through `TASK-0606`, with `TASK-0233` through `TASK-0236` completed as prerequisite planning/platform hygiene and runtime safety hardening.
- `TASK-0235` closes artifact storage confinement and auth-before-read as repo runtime safety posture; `TASK-0236` closes transaction composition safety for schedule-control and logistics-handoff handlers.
- CAPEX runtime activation remains blocked until imported P0, three-project, data-governance, capacity/restore, release, and production-preflight gates close or receive explicit waivers.
- Logistics weekly/live/workpages remain the current implementation focus unless a CAPEX task explicitly changes shared platform semantics.
