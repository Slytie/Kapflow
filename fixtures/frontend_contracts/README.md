# Frontend Contract Snapshots

These JSON files are backend-owned frontend contract fixtures.

They are generated from real runtime scenario states, not hand-authored.

## Refresh workflow
1. Re-generate fixtures:
   - `make frontend-snapshots`
2. Verify fixtures match scenario-backed exports:
   - `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py --check`
   - `PYTHONPATH=/tmp/onetruth-py311:src pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`

## Snapshot set
- `stage06_publish_ready_board_state.json`
- `stage06_needs_information_state.json`
- `stage07_major_replan_board_state.json`
- `stage07_exception_branch_state.json`
- `approval_queue_state.json`
- `run_detail_state.json`
- `timeline_state.json`
- `official_outputs_pointers_state.json`
- `schedule_stage06_needs_info_snapshot.json`
- `workpage_schedule_v0_run_state.json`
- `workpage_schedule_v0_artifact_state.json`
- `workpage_schedule_v0_artifact_submit_response.json`
- `workpage_route_demand_v0_run_state.json`
- `workpage_route_demand_v0_artifact_state.json`
- `workpage_route_demand_v0_artifact_submit_response.json`
- `workpage_driver_preferences_v0_run_state.json`
- `workpage_driver_preferences_v0_artifact_create_response.json`
- `workpage_driver_preferences_v0_artifact_state.json`
- `workpage_driver_preferences_v0_artifact_submit_response.json`
- `workspace_schedule_workpage_action_available_state.json`
- `workspace_schedule_workpage_action_unavailable_state.json`
- `workspace_eod_workpage_action_create_state.json`
- `workspace_eod_workpage_action_open_state.json`
- `workpage_eod_v0_run_state.json`
- `workpage_eod_v0_run_artifact_create_response.json`
- `workpage_eod_v0_artifact_state.json`
- `workpage_eod_v0_artifact_submit_response.json`

These remain backend-owned API contract fixtures and are intentionally distinct from the human-authored planning/oracle fixtures under `fixtures/logistics/workpages/`.
