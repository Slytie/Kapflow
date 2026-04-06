# CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md

## Purpose
Repo-truth snapshot for hardening work. This document states what is currently implemented, what is bounded, and what is still non-claimed.

Scope boundary:
- docs/planning/test-surface alignment only,
- no new runtime semantics,
- conservative status posture (`implemented`, `partial`, `missing`) based on code + tests + runnable entrypoints.

## Certification Run (2026-03-09)
Required validation commands executed:
- `python3 scripts/validate_repo.py` - passed
- `pytest -q tests/contract` - passed
- `pytest -q tests/runtime/contracts/test_workspace_demo_export_bundle.py` - passed
- `pytest -q tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py` - passed
- `pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py` - passed
- `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --db-url sqlite:///.tmp/hardening-matrix-demo.db --scenario stage06_publish_ready --output-root .tmp/hardening-matrix --output-json .tmp/hardening-matrix.json` - passed (`workflow_run_id=wr-497ee868ca8a177576f55d3b`)

Additional verification run in this pass:
- `pytest -q tests/runtime/test_projection_coherence.py` - passed
- `pytest -q tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py` - passed
- `pytest -q tests/runtime/scenarios/test_schedule_stage06_publish_steps.py` - passed
- `pytest -q tests/runtime/scenarios/test_schedule_stage06_request_more_information_steps.py` - passed
- `pytest -q tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py` - passed
- `pytest -q tests/runtime/scenarios/test_workspace_graph_projection.py tests/runtime/api/test_workflow_run_workspace_endpoint.py tests/runtime/api/test_workspace_actionability.py` - passed
- `PYTHONPATH=src pytest -q tests/runtime/api/test_logistics_three_workflow_story_endpoint.py tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py` - passed
- `cd frontend && npm run typecheck` - passed
- `cd frontend && npm run test -- --run src/components/detailDrawer.test.tsx` - passed
- `cd frontend && npm run test -- --run src/pages/logisticsDemoPage.test.tsx` - passed
- `cd frontend && npm run test -- --run src/pages/boardPage.test.tsx` - passed
- `cd frontend && npm run test -- --run src/pages/myWorkPage.test.tsx` - passed
- `cd frontend && npm run test -- --run src/pages/apiIntegrationFlows.test.tsx` - passed
- `cd frontend && npm run test -- --run` - passed
- `cd frontend && npm run build` - passed

## Workpage FE Verification Addendum (2026-03-25)
Additional EPIC-120 verification commands executed:
- `npm --prefix frontend run typecheck` - passed
- `npm --prefix frontend run test:run -- workpage` - passed
- `npm --prefix frontend run test:run -- src/pages/logisticsDemoPage.test.tsx src/lib/repositories/repositoryContracts.test.ts` - passed
- `python3 scripts/validate_repo.py --schemas-only` - passed

## EPIC-121 Artifact-backed Workpage Addendum (2026-03-25)
Additional EPIC-121 verification commands executed:
- `npm --prefix frontend run typecheck` - passed
- `npm --prefix frontend run test:run -- src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsDemoPage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py` - passed
- `python3 scripts/validate_repo.py --schemas-only` - passed

## EPIC-122 Run-backed Schedule Addendum (2026-03-26)
Additional `TASK-0138` verification commands executed:
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_run_schedule_contract.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` - passed
- `python3.11 scripts/validate_repo.py --schemas-only` - passed

## EPIC-122 Run-backed EOD Addendum (2026-03-26)
Additional `TASK-0139` verification commands executed:
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_run_eod_contract.py tests/runtime/api/test_workpages_artifact_eod_contract.py tests/runtime/api/test_workpages_run_schedule_contract.py tests/unit/test_api_route_registry.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` - passed
- `python3.11 scripts/validate_repo.py --schemas-only` - passed

## EPIC-122 Frontend Run-backed Workpage Addendum (2026-03-26)
Additional `TASK-0140` verification commands executed:
- `npm --prefix frontend run typecheck` - passed
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsWorkpageRoutes.test.tsx src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsDemoPage.test.tsx` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` - passed
- `python3.11 scripts/validate_repo.py --schemas-only` - passed

## EPIC-122 Demo/Drilldown Closeout Addendum (2026-03-26)
Additional `TASK-0141` verification commands executed:
- `npm --prefix frontend run test:run -- src/pages/logisticsDemoPage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx` - passed
- `npm --prefix frontend run typecheck` - passed
- `python3.11 scripts/validate_repo.py --schemas-only` - passed

## EPIC-123 Schedule Artifact Slice Addendum (2026-03-26)
Additional `TASK-0142` through `TASK-0145` verification commands executed:
- `python3.11 scripts/validate_repo.py --schemas-only` - passed
- `rg -n "EPIC-123|TASK-0142|TASK-0143|TASK-0144|TASK-0145|planning\\.draft_weekly_schedule\\.workbook|schedule-v0/artifacts|schedule-v0/drafts" docs codex` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/unit/test_schedule_draft_workbook.py tests/runtime/api/test_workpages_artifact_schedule_contract.py tests/runtime/api/test_workpages_artifact_eod_contract.py tests/runtime/api/test_workpages_run_schedule_contract.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` - passed
- `npm --prefix frontend run typecheck` - passed
- `npm --prefix frontend run test:run -- src/lib/api/onetruthApi.workpages.test.ts src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsScheduleWorkpagePage.test.tsx src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx` - passed

## EPIC-124 Stage-linked Workspace Action Closeout Addendum (2026-03-27)
Additional `TASK-0146` through `TASK-0150` verification commands executed:
- `python3 scripts/validate_repo.py --schemas-only` - passed (`4797 check(s) passed`)
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/unit/test_task_requirements.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/api/test_workspace_workpage_actions.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/api/test_workflow_run_workspace_endpoint.py` - passed
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py` - passed
- `npm --prefix frontend run typecheck` - passed
- `npm --prefix frontend run test:run -- --fileParallelism=false src/lib/api/onetruthApi.workspace.test.ts src/pages/runWorkspacePage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx` - passed

Closeout verification notes:
- The EPIC-124 workspace-action fixtures were regenerated in place after a bounded mismatch on `workspace_schedule_workpage_action_available_state.json`.
- The full-corpus reruns `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check` and `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` were relaunched after that bounded fixture rewrite, but they did not return a final result before this closeout pass ended in the current environment.
- `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/api/test_workpages_artifact_schedule_contract.py` was also relaunched during closeout and likewise did not return a final result before this pass ended.

## Weekly Stage04 Pilot Addendum (2026-03-12)
Additional TASK-0070 verification commands executed:
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key verify-task-0070-fresh --openai-mode mock --json` - passed (`workflow_run_id=wr-8802bae7fa0e735404703924`)
- `PYTHONPATH=src pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py tests/runtime/test_weekly_stage04_execution_runtime.py tests/runtime/api/test_weekly_stage04_openai_agent_api.py tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py` - passed
- `PYTHONPATH=src pytest -q tests/integration_openai/test_weekly_stage04_openai_real_e2e.py` - passed (skipped: dual real-network gate not enabled)
- `PYTHONPATH=src pytest -q tests/integration_openai/test_stage06_openai_real_e2e.py` - passed (skipped: real-network gate not enabled)

## Capability Matrix
| Capability | Canonical command / entrypoint | Authoritative tests | Human-inspectable artifacts produced | Invariants that should hold | Current status |
|---|---|---|---|---|---|
| Schedule Stage06 publish-ready demo | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage06_publish_ready ...`<br>`python3 -m onetruth.cli tasks complete` + `approvals request/respond` + `pointers promote` | `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py`<br>`tests/runtime/contracts/test_workspace_demo_export_bundle.py` | `.tmp/hardening-matrix/workspace-demo/stage06_publish_ready/inspection_packet.json`<br>`.tmp/hardening-matrix/workspace-demo/stage06_publish_ready/inspection_packet.md`<br>bundle files (`workspace_projection.json`, `official_outputs.json`, `graph_nodes.json`, `graph_edges.json`) | one-truth chain (`task.completed -> approval.responded -> artifact.pointer.promoted`)<br>no official publish without approval gate<br>Stage06 bounded execution evidence remains canonical (`execution_sessions`, `tool_executions`, `policy_decisions`) | implemented |
| Schedule Stage06 needs-information / recovery path | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage06_needs_information ...`<br>`POST /api/v1/human-tasks/{id}/artifacts/upload` + `GET /api/v1/workflow-runs/{id}/workspace` | `tests/runtime/scenarios/test_schedule_stage06_request_more_information_steps.py`<br>`tests/runtime/api/test_workspace_actionability.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py` | spawned child `Stage06 information_request` task rows/events<br>workspace item fields (`missing_required_inputs`, `available_actions`)<br>artifact linkage evidence after upload | child tasks are explicit (`task.run.created`, `task.created`) not hidden<br>retry/idempotency does not duplicate child work<br>no pointer promotion while information is unresolved | implemented (bounded manual recovery loop) |
| Schedule Stage07 major-replan path | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage07_major_replan ...`<br>`python3 -m onetruth.cli stage07 activate-issue` + `approvals` + `pointers` | `tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py` | Stage07 issue/flag lifecycle rows<br>`schedule.replan_delta.workbook` artifacts<br>`official:schedule.replan_delta.workbook` pointer promotion evidence | major replan promotion requires approval (`official_major_replan` gate)<br>base schedule remains immutable; replan is additive delta<br>issue lineage remains bound to canonical flag/task context | implemented |
| Weekly Stage04 OpenAI pilot + inspection packet | `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key verify-task-0070-fresh --openai-mode mock --json`<br>`POST /api/v1/human-tasks/{id}/weekly-stage04-openai-agent` | `tests/runtime/test_logistics_weekly_agent_pilot.py`<br>`tests/runtime/test_weekly_stage04_execution_runtime.py`<br>`tests/runtime/api/test_weekly_stage04_openai_agent_api.py`<br>`tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`<br>`tests/integration_openai/test_weekly_stage04_openai_real_e2e.py` (dual-gated real path) | `artifacts/pilot_runs/logistics_weekly_stage04_agent/<pilot_key>/pilot_summary.json`<br>`artifacts/pilot_runs/logistics_weekly_stage04_agent/<pilot_key>/pilot_summary.md`<br>`artifacts/pilot_runs/logistics_weekly_stage04_agent/<pilot_key>/<pilot_id>/inspection_packet.json`<br>`artifacts/pilot_runs/logistics_weekly_stage04_agent/<pilot_key>/<pilot_id>/inspection_packet.md` | one-truth execution chain (`execution_sessions` + `tool_executions` + `policy_decisions` + `artifact.version.created` evidence)<br>inspection packet must reference canonical IDs/events/evidence artifacts and query routes<br>real-network Stage04 e2e must require both `ONETRUTH_RUN_OPENAI_E2E=1` and `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1` | implemented (mock certified, real-network deliberately gated) |
| Weekly->live logistics handoff slice (`materialize_seed`) | `python3 -m onetruth.cli handoffs materialize-weekly-seeds --json '<payload>'`<br>`python3 -m onetruth.cli handoffs activate-live-dispatch --json '<payload>'` | `tests/runtime/test_logistics_handoff_runtime.py`<br>`tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py` | `edge_executions` rows (`prepared`/`activated`)<br>Stage07 seed artifacts (`planning.daily_dispatch_seed.workbook`)<br>live dispatch run + `workflow_run_inputs` exact bindings | one logical handoff per `(edge_id, source_artifact, target_partition)`<br>same-scope input binding enforcement (`tenant_id`, `domain_id`)<br>replay-safe activation (no duplicate target run) | implemented (first slice) |
| Reporting->planning logistics notify-only slice | `python3 -m onetruth.cli handoffs notify-only --json '<payload>'` | `tests/runtime/test_logistics_handoff_runtime.py`<br>`tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py` | `edge_executions` row for `reporting_actuals_to_future_planning`<br>target `weekly_schedule_planning.v1` run resolution/creation<br>target input artifact (`planning.actual_hours_snapshot.workbook`) + input binding | compiled-edge mode gate (`handoff_mode=notify_only`, `writer_mode=source_only`)<br>idempotent edge reuse and target-run resolution<br>no target-side official output mutation or pointer side effects | implemented (bounded first notify-only slice) |
| Logistics primary demo shell + drawer-first task transitions | frontend route `/demo/logistics` backed by `GET /api/v1/stories/logistics-three-workflow`; human-task board-card primary click opens drawer; drawer task actions call canonical task routes (`GET /api/v1/human-tasks/{id}`, `POST .../claim`, `POST .../complete`, `POST .../stage06-agent-review`, `POST .../confirm-review`, `POST .../artifacts/upload`) | `frontend/src/pages/logisticsDemoPage.test.tsx`<br>`frontend/src/components/detailDrawer.test.tsx`<br>`frontend/src/pages/apiIntegrationFlows.test.tsx`<br>`tests/runtime/api/test_logistics_three_workflow_story_endpoint.py` | interactive drawer task context (identity/state/assignee/blocking/missing inputs/actions), canonical workpage launch links for linked weekly/reporting runs, run-specific workpage CTAs in family-node drilldowns, task artifact download, and refreshed board/queue states in UI tests | task transitions remain canonical API mutations only<br>drawer actionability is driven by server fields (`available_actions`, `blocking_reason_codes`, `missing_required_inputs`)<br>`/demo/logistics` is a shell entrypoint only and launches canonical `/runs/{workflow_run_id}/workpages/*` pages | implemented |
| Logistics canonical workpages v1 (`schedule-v0`, `route-demand-v0`, `driver-preferences-v0`, `eod-v0`) | frontend routes under `/runs/:workflowRunId/workpages/*` backed by canonical run/kind-scoped backend workpage routes plus canonical nested artifact read/submit/preview/create flows | `frontend/src/pages/logisticsScheduleWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsRouteDemandWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsDriverPreferencesWorkpagePage.test.tsx`<br>`frontend/src/pages/dispatchReportWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsWorkpageRoutes.test.tsx`<br>`tests/runtime/contracts/test_frontend_snapshot_fixtures.py` | backend-generated canonical workpage snapshots for run-backed landings, artifact-backed editors/history pages, live schedule preview, route-demand drift, and driver-preference advisory cues | workpages remain derived surfaces only<br>`schedule-v0` is reassignment/recalculation only<br>`route-demand-v0` owns demand truth edits<br>`driver-preferences-v0` remains advisory only<br>accepted history and draft lineage stay separate | implemented |
| Workflow-run-backed schedule workpage slice | backend route `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`, frontend route `/runs/:workflowRunId/workpages/schedule-v0`, and generated frontend contract fixture `fixtures/frontend_contracts/workpage_schedule_v0_run_state.json` | `tests/runtime/api/test_workpages_run_schedule_contract.py`<br>`frontend/src/pages/logisticsScheduleWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsWorkpageRoutes.test.tsx`<br>`tests/runtime/contracts/test_frontend_snapshot_fixtures.py` | backend-generated run-backed schedule snapshot over a real seeded weekly run with canonical Stage04 input artifacts plus a live frontend route over the same contract | route stays composite/query-backed rather than artifact-backed<br>response adds `run_context` while keeping the existing inner `WorkpageViewModel` stable<br>missing required Stage04 inputs fail cleanly as `409 workpage_projection_unavailable` instead of falling back to demo defaults<br>demo schedule page remains a compatibility alias rather than the only active access model | implemented |
| Artifact-backed schedule draft/review slice (bounded Stage04 workbook lane) | frontend route `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId` plus canonical nested artifact read/submit/preview routes and `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` for history discovery | `tests/unit/test_schedule_draft_workbook.py`<br>`tests/runtime/api/test_workpages_artifact_schedule_contract.py`<br>`frontend/src/lib/api/onetruthApi.workpages.test.ts`<br>`frontend/src/lib/repositories/workpagesRepository.test.ts`<br>`frontend/src/pages/logisticsScheduleWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsScheduleArtifactWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsWorkpageRoutes.test.tsx`<br>`tests/runtime/contracts/test_frontend_snapshot_fixtures.py` | backend-generated schedule artifact read/submit snapshots, canonical run-backed landing handoff to the newest Stage04 draft workbook artifact, immutable superseding schedule draft versions, recent draft history, live preview recalculation, and truthful JSON download | edit surface stays anchored to `planning.draft_weekly_schedule.workbook` only<br>no `schedule-v0/drafts` create route because Stage04 already emits the initial draft workbook<br>submit creates a new immutable draft artifact version and conflicts fail closed against the latest chain head<br>Stage06 publish, Stage07 seed editing, live-dispatch control, and generic spreadsheet-editor scope remain out of scope | implemented |
| Workflow-run-backed EOD landing slice | backend routes `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0` and `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`, frontend routes `/runs/:workflowRunId/workpages/eod-v0` and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`, plus generated frontend contract fixtures `fixtures/frontend_contracts/workpage_eod_v0_run_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_run_artifact_create_response.json` | `tests/runtime/api/test_workpages_run_eod_contract.py`<br>`tests/runtime/api/test_workpages_artifact_eod_contract.py`<br>`frontend/src/pages/dispatchReportWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsWorkpageRoutes.test.tsx`<br>`frontend/src/lib/repositories/workpagesRepository.test.ts`<br>`tests/runtime/contracts/test_frontend_snapshot_fixtures.py`<br>`tests/unit/test_api_route_registry.py` | backend-generated run-backed EOD landing snapshot over a real seeded reporting run plus the canonical run-backed create-response fixture used by the active frontend handoff | landing remains derived and read-only while artifact-backed editing stays on the existing workbook route<br>response adds `run_context` plus EOD-only `draft_resolution` and leaves `artifact_context` absent<br>latest-draft resolution uses the newest compatible `reporting.upd_draft.workbook` artifact inside the supplied workflow run<br>run-backed landing CTA now follows `draft_resolution` truthfully instead of guessing | implemented |
| Artifact-backed EOD draft/review slice (immutable workbook chain) | frontend route `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId` plus canonical run-backed create route, canonical nested artifact read/submit routes, and `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` | `frontend/src/lib/repositories/workpagesRepository.test.ts`<br>`frontend/src/pages/dispatchReportWorkpagePage.test.tsx`<br>`frontend/src/pages/logisticsWorkpageRoutes.test.tsx`<br>`frontend/src/pages/logisticsDemoPage.test.tsx`<br>`tests/runtime/api/test_workpages_artifact_eod_contract.py`<br>`tests/runtime/contracts/test_frontend_snapshot_fixtures.py` | backend-generated create/read/submit snapshots for the artifact-backed EOD flow, immutable workbook versions downloadable through the normal artifact binary route, and a recent draft history panel sourced from workflow-run artifact truth | drafts stay anchored to canonical `dispatch_reporting.v1` runs<br>submit creates a new immutable workbook version and conflicts fail closed against the latest chain head<br>recent history comes from canonical workflow-run artifact truth, not frontend-local version state<br>submit/conflict handoff routes stay inside canonical nested `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` paths | implemented |
| Authoritative workspace/export/graph surfaces | `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`<br>`PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py --db-url <db> --workflow-run-id <id> --output <zip>` | `tests/runtime/scenarios/test_workspace_graph_projection.py`<br>`tests/runtime/api/test_workflow_run_workspace_endpoint.py`<br>`tests/runtime/api/test_workspace_actionability.py`<br>`tests/runtime/contracts/test_workspace_demo_export_bundle.py` | workspace payload (`graph`, `user_work`, `blocking_work`, `official_outputs`, `timeline_excerpt`)<br>bundle ZIP with required JSON files + `README.md` | projection is derived and non-authoritative<br>server-computed actionability (`available_actions`, `missing_required_inputs`)<br>cross-scope access fails closed | implemented (schedule_planning.v1 graph projector scope) |
| Projection coherence harness (workspace/export/handoff views) | Runtime entrypoints: workspace endpoint, workspace export script, `handoffs show/list`<br>Policy definition: `docs/planning/PROJECTION_COHERENCE_HARNESS.md` | `tests/runtime/test_projection_coherence.py` | visible coherence metadata in payloads<br>blocked export error payload (`projection_coherence_failed`)<br>timeline evidence event `projection.coherence_failed` | block vs warn policy must match projection criticality<br>coherence checks never mutate business truth rows<br>coherence failure is visible and auditable | implemented and authored (both), bounded to 3 projection kinds |

## Projection Coherence Classification
Current state for projection coherence: authored + implemented (both).

Evidence:
- authored policy and checklists in `docs/planning/PROJECTION_COHERENCE_HARNESS.md`,
- runtime behavior in `src/onetruth/application/projections/coherence_harness.py`,
- scenario-backed tests in `tests/runtime/test_projection_coherence.py`.

## Remaining Ambiguities / Bounded Claims
- Real OpenAI network paths (Stage06 and weekly Stage04) were not executed in this pass because real-network env gates were intentionally left disabled; certification here remains mock/runtime-surface only for those slices.
- Workspace graph runtime coverage is currently schedule-planning-specific; this pass does not certify graph projectors for other workflow families.
- Logistics handoff runtime is certified for the implemented weekly->live and reporting->planning edges above; this pass does not claim generalized coverage for every future family edge.
- Workpage routes are certified for the current query-backed schedule/EOD preview surfaces, the run-backed schedule/EOD slices, the bounded artifact-backed EOD slice, and the bounded Stage04 schedule artifact slice only; this pass still does not certify generic artifact editing, Stage06 publish semantics, Stage07/live-dispatch editing, or future workspace/human-task workpage integration.
