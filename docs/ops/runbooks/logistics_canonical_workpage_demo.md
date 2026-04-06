# Logistics Canonical Workpage Demo

## Goal
- Validate the canonical workpage surfaces with the deterministic prep path, not the older OpenAI/full-loop walkthrough.
- Use the canonical `/runs/:workflowRunId/workpages/*` routes as the semantic validation surface.
- Keep this walkthrough lightweight and repeatable. No OpenAI required.

## Supported Toolchain
1. Use Python `3.11` and install backend dependencies with `python3.11 -m pip install -e ".[api,dev]"`.
2. Use Node `20` and install the frontend from the committed lockfile with `cd frontend && npm ci`.
3. Run `make doctor` before the demo if you have not already validated the local toolchain.

## Startup
Backend terminal:
```bash
PYTHONPATH=src onetruth-api \
  --db-url sqlite:///./.tmp/logistics-canonical-workpage-demo.db \
  --host 127.0.0.1 \
  --port 8080 \
  --api-boundary-profile local_dev
```

Frontend terminal:
```bash
cd frontend
VITE_ONETRUTH_API_BASE_URL=http://127.0.0.1:8080/api/v1 npm run dev
```

Optional DB init:
```bash
PYTHONPATH=src python3.11 -m onetruth.cli \
  --db-url sqlite:///./.tmp/logistics-canonical-workpage-demo.db \
  init-db
```

You can skip explicit `init-db` on a fresh DB file because the prep script creates the substrate implicitly.

## Prep Commands
- `scripts/run_logistics_local_demo.py` is the older weekly-first workspace/story walkthrough seed and still assumes the broader operator loop.
- `scripts/run_logistics_workpage_demo_prep.py` is the supported default command for deterministic canonical workpage validation.

Prep terminal:
```bash
PYTHONPATH=src python3.11 scripts/run_logistics_workpage_demo_prep.py \
  --db-url sqlite:///./.tmp/logistics-canonical-workpage-demo.db \
  --output-json .tmp/logistics-canonical-workpage-demo.json
cat .tmp/logistics-canonical-workpage-demo.json
```

Expected output fields:
- `schedule_workpage_url`
- `schedule_artifact_url`
- `route_demand_workpage_url`
- `route_demand_artifact_url`
- `driver_preferences_workpage_url`
- `driver_preferences_artifact_url`
- `eod_workpage_url`

## Walkthrough
Prepend the frontend origin to each emitted route, for example `http://127.0.0.1:5173${schedule_workpage_url}`.

Recommended order:
1. Open `schedule_workpage_url`.
2. Open `schedule_artifact_url`.
3. Open `route_demand_workpage_url`.
4. Open `route_demand_artifact_url`.
5. Open `driver_preferences_workpage_url`.
6. Open `driver_preferences_artifact_url`.
7. Open `eod_workpage_url`.

Optional launcher context:
- `/demo/logistics` can still be opened as narrative/launcher context, but it is not the validation surface for this runbook.

## Intentionally Not Pre-Seeded
- multi-week accepted history
- route-demand auto-drift seed
- live-dispatch completion lane
- pre-created EOD draft artifact
- OpenAI-backed Stage04 execution
