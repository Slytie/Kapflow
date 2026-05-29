# Local Logistics Demo (Beginner Guide)

## What this guide is for

Use this guide when you want to run the **full local logistics demo** with the real `/demo/logistics` story shell, the seeded weekly/reporting runs, and the real OpenAI-backed weekly Stage04 build path.

This is the right guide if you are new to the repo and want the most complete local demo experience.

If you only want a deterministic workpage-only validation path with no OpenAI dependency, use `docs/ops/runbooks/logistics_canonical_workpage_demo.md` instead.

## What you are starting

You will start three things:

1. The backend API on `127.0.0.1:8080`
2. The local demo seeder, which writes a summary JSON file
3. The frontend dev server on `127.0.0.1:5173`

At the end, you will open the story shell at `/demo/logistics`.

## Before you start

### Assumptions

This guide assumes all of the following:

- You are on macOS or Linux, or another environment with a similar shell experience.
- You are working from the repo root.
- You can run `python3.11`.
- You can run Node `20`.
- You have a real `OPENAI_API_KEY`.
- You can keep **three terminals** open at once.

### Required versions

The repo's validated local baseline is:

- Python `3.11`
- Node `20`

Check that first:

```bash
python3.11 --version
node --version
npm --version
pwd
```

You should also confirm that you are actually in the repo root before running anything else.

## One-time local setup

If this machine has not been prepared for this repo yet, do this first.

### 1. Install backend dependencies

From the repo root:

```bash
python3.11 -m pip install -e ".[api,dev]"
```

### 2. Install frontend dependencies

From the repo root:

```bash
cd frontend
npm ci
cd ..
```

`npm ci` is the supported frontend install path for this repo. Do not treat an old `node_modules` directory as trustworthy.

### 3. Validate the local toolchain

Recommended:

```bash
make doctor
```

This is not strictly required before every demo run, but it is a good first check if you are setting up the repo for the first time.

### 4. Verify the local entrypoints exist

These commands should print help text instead of failing:

```bash
onetruth-api --help
python3.11 scripts/run_logistics_local_demo.py --help
python3.11 scripts/run_logistics_demo_frontend.py --help
```

If one of these commands fails, stop and fix the environment before you continue.

## Environment variable you must have

The weekly Stage04 build path uses a real OpenAI key.

Check that the key exists:

```bash
if [ -n "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY is set"
else
  echo "OPENAI_API_KEY is missing"
fi
```

If you see `OPENAI_API_KEY is missing`, export it before continuing.

## Recommended local file paths

This guide uses one stable local DB file and one stable local JSON file:

- DB: `.tmp/logistics-local-demo.db`
- JSON: `.tmp/logistics-local-demo.json`

Using stable filenames makes reseeding and recovery easier.

## Start the demo

Open **three terminals** and keep them open.

### Terminal 1: Start the backend API

Run this from the repo root:

```bash
PYTHONPATH=src onetruth-api \
  --db-url sqlite:///./.tmp/logistics-local-demo.db \
  --host 127.0.0.1 \
  --port 8080 \
  --api-boundary-profile local_dev
```

Important notes:

- `onetruth-api` is the supported local startup path.
- `local_dev` is the correct profile for this demo.
- The host must stay loopback-only unless you deliberately opt into unsafe overrides.

Leave this terminal running.

### Terminal 2: Seed the demo

First confirm the key exists:

```bash
test -n "$OPENAI_API_KEY"
```

Then run the seeder:

```bash
PYTHONPATH=src python3.11 scripts/run_logistics_local_demo.py \
  --db-url sqlite:///./.tmp/logistics-local-demo.db \
  --output-json .tmp/logistics-local-demo.json
```

Then print the saved JSON:

```bash
cat .tmp/logistics-local-demo.json
```

The command should print a JSON payload with `"status": "ok"`.

### Terminal 3: Start the frontend launcher

Run this from the repo root:

```bash
PYTHONPATH=src python3.11 scripts/run_logistics_demo_frontend.py \
  --demo-json .tmp/logistics-local-demo.json
```

This launcher is important. It injects the correct local-dev trusted-header context so the frontend sees the seeded `tenant-logistics / domain-hub` runtime state automatically.

Do **not** replace this with a raw `npm run dev` unless you are intentionally debugging frontend env wiring.

Leave this terminal running too.

## What success looks like before you open the browser

Do these checks in order.

### Backend success signals

The backend terminal should:

- stay running
- show no import error or traceback
- bind to `127.0.0.1:8080`

If you want to check the port directly:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

### Seeder success signals

The seeder output JSON should include:

- `"status": "ok"`
- `"openai_api_key_present": true`
- `"recommended_story_url"`
- `"weekly_workspace_url"`
- `"reporting_workspace_url"`
- `"review_ready_weekly_workspace_url"`
- `"review_ready_schedule_workpage_url"`
- `"review_ready_route_demand_workpage_url"`
- `"review_ready_driver_preferences_workpage_url"`
- `"review_ready_reporting_workspace_url"`
- `"review_ready_eod_workpage_url"`

If `openai_api_key_present` is `false`, the weekly Stage04 real-agent path is not correctly configured.

### Frontend success signals

The frontend terminal should:

- print the active demo scope and actor
- print routes from the demo JSON
- start Vite successfully
- expose the local frontend on `http://127.0.0.1:5173`

If you want to check the port directly:

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

## How to read the seed JSON

The seed JSON is the source of truth for the local demo you just created.

The most important keys are:

- `recommended_story_url`
  Use this first. It is the main `/demo/logistics` story-shell URL.
- `weekly_workspace_url`
  The scratch weekly workspace. Use this for the full intake -> Stage04 -> review -> publish walkthrough.
- `reporting_workspace_url`
  The scratch reporting workspace. Use this for the EOS intake -> draft -> review lane from the beginning.
- `live_workspace_url`
  This is `null` before weekly publish. That is expected.
- `prepare_live_dispatch_path`
  The backend path the shell uses when weekly publish has succeeded and you prepare the live-dispatch day.
- `review_ready_weekly_workspace_url`
  The seeded weekly companion workspace.
- `review_ready_schedule_workpage_url`
  The fastest direct path to the seeded weekly schedule workpage.
- `review_ready_route_demand_workpage_url`
  The fastest direct path to the seeded weekly route-demand workpage.
- `review_ready_driver_preferences_workpage_url`
  The fastest direct path to the seeded weekly driver-preferences workpage.
- `review_ready_reporting_workspace_url`
  The seeded reporting companion workspace.
- `review_ready_eod_workpage_url`
  The fastest direct path to the seeded EOD workpage.

If you are ever unsure which URL to open, check `.tmp/logistics-local-demo.json` before guessing.

## Understand the seeded demo before you click anything

This seeder creates a **combined demo**, not just one single workflow run.

### Scratch runs

These are the "start from intake and do the real steps" runs:

- `weekly_workspace_url`
- `reporting_workspace_url`

Use these when you want to test the older full walkthrough behavior from the beginning.

### Review-ready companion runs

These are already advanced to seeded review-ready states so newer workpage surfaces are immediately available:

- `review_ready_weekly_workspace_url`
- `review_ready_schedule_workpage_url`
- `review_ready_route_demand_workpage_url`
- `review_ready_driver_preferences_workpage_url`
- `review_ready_reporting_workspace_url`
- `review_ready_eod_workpage_url`

Use these when you want to inspect seeded workpage surfaces immediately.

### Important weekly rule

The **scratch weekly run** is not the same thing as the **review-ready weekly run**.

That means:

- the scratch weekly run is for intake -> Stage04 -> review -> publish walkthrough testing
- the review-ready weekly run is for seeded schedule, route-demand, and driver-preferences workpage testing

If you open weekly workpages from the wrong run, they may look empty or return a `409` because that run is not ready for that surface yet.

## Open the demo in the browser

The main entrypoint is the story shell.

If you used the default seed values, open:

```text
http://127.0.0.1:5173/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06
```

More generally, open the value from `recommended_story_url` under the frontend origin:

```text
http://127.0.0.1:5173${recommended_story_url}
```

## Two common ways to use this demo

Choose the path that matches what you are trying to test.

### Path A: Full walkthrough from intake

Use this when you want to exercise the older end-to-end operator flow.

1. Open the story shell.
2. Click `Open weekly workspace`.
3. Work from the **scratch weekly run**.
4. Claim `Weekly Input Intake`.
5. Upload the weekly input files from `fixtures/logistics/local_demo_upload_pack/weekly/`.
6. Complete the intake task.
7. Claim `Run Stage04 Build`.
8. Run the Stage04 build and wait for it to finish.
9. Complete the Stage04 build task.
10. Claim `Final Review`.
11. Open the schedule workpage from that review task.
12. Make an edit and submit a new draft.
13. Return to the workspace.
14. Upload `weekly_manager_review.docx`.
15. Confirm review against the latest draft.
16. Complete the review task.
17. Approve the publish approval.
18. Return to `/demo/logistics`.
19. Use the story shell to prepare live dispatch when the publish path makes it available.
20. Open the live-dispatch workspace after the prepare step succeeds.
21. Claim `Prepare Live Day Inputs`.
22. Upload `live/live_route_delta_small_change.xlsx`.
23. Complete the live intake task.
24. Claim `Review Live Replan`.
25. Upload `live/live_dispatcher_review.docx`.
26. Confirm review against the latest live replan artifact.
27. Complete the live review task.
28. Return to `/demo/logistics`.
29. Open the reporting workspace from the scratch reporting run.
30. Claim `EOS Input Intake`.
31. Upload `reporting/reporting_eos_raw.xlsx`.
32. Complete the intake task.
33. Claim `Final Packet Review`.
34. Open the EOD workpage from that review task.
35. Make an edit and submit a new draft.
36. Return to the workspace.
37. Confirm review against the latest EOD draft workbook.
38. Complete the review task.
39. Approve the reporting approval.

### Path B: Immediate seeded workpage review

Use this when you want to inspect newer weekly/reporting surfaces without first walking the scratch runs forward.

Open these URLs from the seed JSON:

- `review_ready_schedule_workpage_url`
- `review_ready_route_demand_workpage_url`
- `review_ready_driver_preferences_workpage_url`
- `review_ready_eod_workpage_url`

With the default seed, that means:

- review-ready weekly schedule
- review-ready weekly route demand
- review-ready weekly driver preferences
- review-ready reporting EOD

This is the fastest way to test seeded workpage behavior.

## Upload pack reference

The local upload pack root is:

```text
fixtures/logistics/local_demo_upload_pack
```

### Weekly files

- `weekly/weekly_route_slot_requirements.xlsx`
- `weekly/weekly_approved_availability.xlsx`
- `weekly/weekly_driver_capabilities.xlsx`
- optional `weekly/weekly_actual_hours_snapshot_optional.xlsx`
- `weekly/weekly_manager_review.docx`

### Live-dispatch files

- `live/live_route_delta_small_change.xlsx`
- `live/live_dispatcher_review.docx`

### Reporting files

- `reporting/reporting_eos_raw.xlsx`

Important reporting note:

- the upload pack still contains `reporting/reporting_manager_review.docx`
- the current primary reporting review lane no longer requires that file for the first operator path
- current reporting review confirmation is workbook-based

## How to reset and reseed the demo

If the demo gets out of sync, the simplest recovery is a clean reseed.

### Fast reset procedure

1. Stop the frontend terminal with `Ctrl+C`.
2. Stop the backend terminal with `Ctrl+C`.
3. From the repo root, remove the old local DB and JSON:

```bash
rm -f .tmp/logistics-local-demo.db .tmp/logistics-local-demo.json
```

4. Start the backend again.
5. Run the seeder again.
6. Start the frontend launcher again.
7. Refresh the browser.

### Browser refresh rule

After reseeding, do a hard refresh if the browser still looks stale.

A plain refresh is often enough, but if the shell or seeded workpages still look wrong, use a hard reload.

## Troubleshooting

This section is written for someone who does not already know the repo's demo habits.

### Problem: `OPENAI_API_KEY` is missing

Symptoms:

- the environment check says the key is missing
- the seed JSON says `"openai_api_key_present": false`
- the weekly Stage04 build cannot run correctly

What to do:

1. Export a real key into your shell.
2. Rerun the seeder.
3. Confirm the JSON now says `"openai_api_key_present": true`.

### Problem: the backend is not running on `127.0.0.1:8080`

Check:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

If nothing is listening, start the backend again.

If the wrong process is listening, stop that process before restarting the demo backend.

### Problem: the frontend is not running on `127.0.0.1:5173`

Check:

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

If nothing is listening, restart the frontend launcher.

If another process already owns the port, stop that process or restart the frontend cleanly.

### Problem: one of the ports is already in use

Check the owner:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

Then stop the stale process:

```bash
kill <pid>
```

After that, rerun the backend or frontend command on the normal ports.

### Problem: the seed file exists, but weekly pages show no seeded data

This is usually a **run selection problem**, not missing data.

Check whether you opened a scratch weekly route instead of a review-ready weekly route.

For seeded weekly workpages, use:

- `review_ready_schedule_workpage_url`
- `review_ready_route_demand_workpage_url`
- `review_ready_driver_preferences_workpage_url`

Do **not** assume the scratch weekly run already has those seeded surfaces.

If you are unsure, open the URLs directly from `.tmp/logistics-local-demo.json`.

### Problem: the browser looks stale after a reseed

What to do:

1. Refresh the tab.
2. If that is not enough, hard refresh the tab.
3. If it is still wrong, stop and restart the frontend launcher.
4. If it is still wrong after that, do the full reset/reseed flow.

### Problem: the weekly Stage04 build fails

What to check:

1. Confirm `OPENAI_API_KEY` is set.
2. Confirm the seed JSON says `"openai_api_key_present": true`.
3. Read the backend terminal for the actual error.
4. If the run is now in a bad intermediate state, reseed from a clean DB and try again.

Important nuance:

- the runtime can do one bounded finalize-only recovery if the model exits without the required finalize call
- if finalize still does not happen, the run still fails closed

For a beginner operator demo, the simplest recovery is usually a fresh reseed.

### Problem: the frontend loads, but the story shell does not match the seed

Make sure you launched the frontend with:

```bash
PYTHONPATH=src python3.11 scripts/run_logistics_demo_frontend.py --demo-json .tmp/logistics-local-demo.json
```

If you launched raw `npm run dev`, the frontend may not have the correct trusted-header demo context.

### Problem: the seeder did not write the expected JSON

Check that:

- the backend dependencies were installed
- the DB path is writable
- you ran the command from the repo root

Then rerun:

```bash
PYTHONPATH=src python3.11 scripts/run_logistics_local_demo.py \
  --db-url sqlite:///./.tmp/logistics-local-demo.db \
  --output-json .tmp/logistics-local-demo.json
```

## What to remember

If you only remember five things, remember these:

1. Start the backend first.
2. Then run the seeder and read the JSON.
3. Then start the frontend with `scripts/run_logistics_demo_frontend.py`.
4. Open `/demo/logistics` from `recommended_story_url`.
5. Use the **review-ready** URLs for immediate seeded weekly/reporting workpage testing.
