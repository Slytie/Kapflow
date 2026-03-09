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

## Capability Matrix
| Capability | Canonical command / entrypoint | Authoritative tests | Human-inspectable artifacts produced | Invariants that should hold | Current status |
|---|---|---|---|---|---|
| Schedule Stage06 publish-ready demo | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage06_publish_ready ...`<br>`python3 -m onetruth.cli tasks complete` + `approvals request/respond` + `pointers promote` | `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py`<br>`tests/runtime/contracts/test_workspace_demo_export_bundle.py` | `.tmp/hardening-matrix/workspace-demo/stage06_publish_ready/inspection_packet.json`<br>`.tmp/hardening-matrix/workspace-demo/stage06_publish_ready/inspection_packet.md`<br>bundle files (`workspace_projection.json`, `official_outputs.json`, `graph_nodes.json`, `graph_edges.json`) | one-truth chain (`task.completed -> approval.responded -> artifact.pointer.promoted`)<br>no official publish without approval gate<br>Stage06 bounded execution evidence remains canonical (`execution_sessions`, `tool_executions`, `policy_decisions`) | implemented |
| Schedule Stage06 needs-information / recovery path | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage06_needs_information ...`<br>`POST /api/v1/human-tasks/{id}/artifacts/upload` + `GET /api/v1/workflow-runs/{id}/workspace` | `tests/runtime/scenarios/test_schedule_stage06_request_more_information_steps.py`<br>`tests/runtime/api/test_workspace_actionability.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py` | spawned child `Stage06 information_request` task rows/events<br>workspace item fields (`missing_required_inputs`, `available_actions`)<br>artifact linkage evidence after upload | child tasks are explicit (`task.run.created`, `task.created`) not hidden<br>retry/idempotency does not duplicate child work<br>no pointer promotion while information is unresolved | implemented (bounded manual recovery loop) |
| Schedule Stage07 major-replan path | `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --scenario stage07_major_replan ...`<br>`python3 -m onetruth.cli stage07 activate-issue` + `approvals` + `pointers` | `tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`<br>`tests/runtime/test_realistic_schedule_planning_pilot.py` | Stage07 issue/flag lifecycle rows<br>`schedule.replan_delta.workbook` artifacts<br>`official:schedule.replan_delta.workbook` pointer promotion evidence | major replan promotion requires approval (`official_major_replan` gate)<br>base schedule remains immutable; replan is additive delta<br>issue lineage remains bound to canonical flag/task context | implemented |
| Weekly->live logistics handoff slice (`materialize_seed`) | `python3 -m onetruth.cli handoffs materialize-weekly-seeds --json '<payload>'`<br>`python3 -m onetruth.cli handoffs activate-live-dispatch --json '<payload>'` | `tests/runtime/test_logistics_handoff_runtime.py`<br>`tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py` | `edge_executions` rows (`prepared`/`activated`)<br>Stage07 seed artifacts (`planning.daily_dispatch_seed.workbook`)<br>live dispatch run + `workflow_run_inputs` exact bindings | one logical handoff per `(edge_id, source_artifact, target_partition)`<br>same-scope input binding enforcement (`tenant_id`, `domain_id`)<br>replay-safe activation (no duplicate target run) | implemented (first slice) |
| Reporting->planning logistics notify-only slice | `python3 -m onetruth.cli handoffs notify-only --json '<payload>'` | `tests/runtime/test_logistics_handoff_runtime.py`<br>`tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py` | `edge_executions` row for `reporting_actuals_to_future_planning`<br>target `weekly_schedule_planning.v1` run resolution/creation<br>target input artifact (`planning.actual_hours_snapshot.workbook`) + input binding | compiled-edge mode gate (`handoff_mode=notify_only`, `writer_mode=source_only`)<br>idempotent edge reuse and target-run resolution<br>no target-side official output mutation or pointer side effects | implemented (bounded first notify-only slice) |
| Logistics primary demo shell + drawer-first task transitions | frontend route `/demo/logistics` backed by `GET /api/v1/stories/logistics-three-workflow`; human-task board-card primary click opens drawer; drawer task actions call canonical task routes (`GET /api/v1/human-tasks/{id}`, `POST .../claim`, `POST .../complete`, `POST .../stage06-agent-review`, `POST .../confirm-review`, `POST .../artifacts/upload`) | `frontend/src/pages/logisticsDemoPage.test.tsx`<br>`frontend/src/components/detailDrawer.test.tsx`<br>`frontend/src/pages/apiIntegrationFlows.test.tsx`<br>`tests/runtime/api/test_logistics_three_workflow_story_endpoint.py` | interactive drawer task context (identity/state/assignee/blocking/missing inputs/actions), in-drawer run drill-down link, task artifact download, and refreshed board/queue states in UI tests | task transitions remain canonical API mutations only<br>drawer actionability is driven by server fields (`available_actions`, `blocking_reason_codes`, `missing_required_inputs`)<br>post-action query invalidation keeps story + queue/run views synchronized | implemented (demo-primary; schedule-era routes secondary) |
| Authoritative workspace/export/graph surfaces | `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`<br>`PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py --db-url <db> --workflow-run-id <id> --output <zip>` | `tests/runtime/scenarios/test_workspace_graph_projection.py`<br>`tests/runtime/api/test_workflow_run_workspace_endpoint.py`<br>`tests/runtime/api/test_workspace_actionability.py`<br>`tests/runtime/contracts/test_workspace_demo_export_bundle.py` | workspace payload (`graph`, `user_work`, `blocking_work`, `official_outputs`, `timeline_excerpt`)<br>bundle ZIP with required JSON files + `README.md` | projection is derived and non-authoritative<br>server-computed actionability (`available_actions`, `missing_required_inputs`)<br>cross-scope access fails closed | implemented (schedule_planning.v1 graph projector scope) |
| Projection coherence harness (workspace/export/handoff views) | Runtime entrypoints: workspace endpoint, workspace export script, `handoffs show/list`<br>Policy definition: `docs/planning/PROJECTION_COHERENCE_HARNESS.md` | `tests/runtime/test_projection_coherence.py` | visible coherence metadata in payloads<br>blocked export error payload (`projection_coherence_failed`)<br>timeline evidence event `projection.coherence_failed` | block vs warn policy must match projection criticality<br>coherence checks never mutate business truth rows<br>coherence failure is visible and auditable | implemented and authored (both), bounded to 3 projection kinds |

## Projection Coherence Classification
Current state for projection coherence: authored + implemented (both).

Evidence:
- authored policy and checklists in `docs/planning/PROJECTION_COHERENCE_HARNESS.md`,
- runtime behavior in `src/onetruth/application/projections/coherence_harness.py`,
- scenario-backed tests in `tests/runtime/test_projection_coherence.py`.

## Remaining Ambiguities / Bounded Claims
- Real OpenAI network path was not certified in this pass (`openai_mode=mock` was used for the required workspace-demo command).
- Workspace graph runtime coverage is currently schedule-planning-specific; this pass does not certify graph projectors for other workflow families.
- Logistics handoff runtime is certified for the implemented weekly->live and reporting->planning edges above; this pass does not claim generalized coverage for every future family edge.
