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
- `frontend_request_context`
- `schedule_workpage_url`
- `schedule_artifact_url`
- `route_demand_workpage_url`
- `route_demand_artifact_url`
- `driver_preferences_workpage_url`
- `driver_preferences_artifact_url`
- `eod_workpage_url`

Frontend terminal:
```bash
PYTHONPATH=src python3.11 scripts/run_logistics_demo_frontend.py \
  --demo-json .tmp/logistics-canonical-workpage-demo.json
```

Restart note:
- After changing workpage API routes, action wiring, or frontend workpage code, restart both the backend and frontend processes before validating the live demo again.
- A stale local backend or stale frontend bundle can make route-demand actions appear to save while never reaching the current `/save-and-run` route.

The launcher reads `frontend_request_context` from the prep JSON and injects the matching
local-dev trusted headers so the browser sees the seeded `tenant-logistics / domain-hub`
runtime state instead of the generic local frontend defaults.

## Walkthrough
The frontend launcher prints the active demo routes from the prep JSON as it starts. Use those
route paths under the frontend origin, for example `http://127.0.0.1:5173${schedule_workpage_url}`.

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

### Optional Future-Week Scheduling Demo
- This path is optional and extends the base deterministic walkthrough. It requires a configured weekly Stage04 agent runner.
- Open `route_demand_artifact_url`.
- Confirm only the current operational week is visible.
- Use `Add a week` and choose the offered next week option.
- On the future-week artifact, add at least one `0 -> N` route change.
- Use `Save route demand` for persistence-only validation, or `Save and run scheduling agent` to trigger the weekly Stage04 agent from route demand.
- While the scheduling run is active, the route-demand surface should show `Agent working`.
- On success, the app should navigate to the future run’s canonical `schedule-v0` route and auto-open the existing quick-edit popup on the newest draft.

### Optional Existing-Week Coverage Demo
- This path is optional and stays entirely in the pre-publish weekly-draft lane. It does not use live dispatch.
- Open `route_demand_artifact_url`.
- Increase one or more visible planned route counts on the current operational week.
- Use `Run coverage agent`.
- The route-demand popup should close, the app should navigate to the canonical `schedule-v0` artifact route for the current weekly draft, and the existing quick-edit popup should open automatically.
- Review the backend-ranked coverage recommendation panel above the normal schedule edit surface.
- Apply a selectable recommendation.
- On success, the popup should remain on the successor schedule draft created by the backend apply path.

Recovery note:
- If a prior future-week scheduling attempt stays stuck on `Agent working`, reconcile stale execution sessions before retrying:
```bash
PYTHONPATH=src python3.11 -m onetruth.cli \
  --db-url sqlite:///./.tmp/logistics-canonical-workpage-demo.db \
  maintenance reconcile-executions \
  --json '{"stale_seconds":0}'
```
- Reconciliation marks the stale execution session failed, but it does not make an already-used idempotent `save-and-run` request retryable. After reconciling, use a fresh future route-demand artifact version or reseed the local demo before retrying.

## Intentionally Not Pre-Seeded
- multi-week accepted history
- route-demand auto-drift seed
- live-dispatch completion lane
- pre-created EOD draft artifact
- mandatory OpenAI-backed Stage04 execution for the base walkthrough
