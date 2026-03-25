# Frontend Contract Snapshots

These JSON files are backend-owned frontend contract fixtures.

They are generated from real runtime scenario states, not hand-authored.

## Refresh workflow
1. Re-generate fixtures:
   - `make frontend-snapshots`
2. Verify fixtures match scenario-backed exports:
   - `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`
   - `PYTHONPATH=src pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`

## Snapshot set
- `stage06_publish_ready_board_state.json`
- `stage06_needs_information_state.json`
- `stage07_major_replan_board_state.json`
- `stage07_exception_branch_state.json`
- `approval_queue_state.json`
- `run_detail_state.json`
- `timeline_state.json`
- `official_outputs_pointers_state.json`
- `workpage_schedule_v0_state.json`

## Reserved future workpage snapshots
Future backend demo workpage route snapshots also belong here, for example:
- `workpage_eod_v0_state.json`

These remain backend-owned API contract fixtures and are intentionally distinct from the human-authored planning/oracle fixtures under `fixtures/logistics/workpages/`.
