---
id: TASK-0155
epic: EPIC-125
title: "Add the local FE/BE demo runbook, seeded operator smoke path, and demo entrypoints for the first user test"
status: DONE
owners: ["backend", "frontend", "docs"]
reviewers: ["qa"]
depends_on: ["TASK-0152", "TASK-0153", "TASK-0154"]
risk: medium
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The first serious local FE/BE demo should happen before cadence automation and before hardening. This task creates the runbook and operator path for that demo.

## Scope
- document how to run backend and frontend locally for the operational lane
- add or update seeded demo data / demo entrypoints needed to walk the weekly + daily loop locally
- document the exact click path and required uploads for the first operator demo
- add a compact smoke path proving the local loop is runnable by a human tester
- explicitly mark this as the start point for UI/user feedback collection

## Out of scope
- external cadence automation
- production deployment wiring
- broad UX hardening

## Acceptance signals
- a developer or SME can bring FE and BE up locally and walk the intended operator flow
- the runbook clearly says when local demoing should start
- feedback capture is expected and explicit

## Implemented loop
1. Seed the weekly-first local demo through `scripts/run_logistics_local_demo.py`, which initializes substrate, creates the current weekly and reporting runs, creates the prior reporting-feedback run, and emits stable JSON URLs plus deterministic run ids.
2. Start the walkthrough from `/demo/logistics?planning_week_id=...&service_date_id=...`, which now presents a workspace-first `Start Here` shell with weekly and reporting entrypoints plus a live `Prepare service day` action only after weekly publish truth exists.
3. Walk the canonical weekly operator lane from `Stage04/weekly_input_intake` through Stage04 build, schedule review, and Stage06 publish approval using the bounded upload pack and the real OpenAI-backed Stage04 build.
4. Prepare the service day from the demo shell, then walk the bounded live small-change lane in `live_dispatch.v1` without adding a live workpage route family.
5. Finish in the reporting workspace by uploading EOS input, reviewing the generated EOD draft, and approving finalization so planning feedback truth is visible in the story shell.

## Stop lines kept
- no new workpage or story route family
- no local mock product seam for weekly Stage04 human demoing
- no replacement of the existing full-lineage three-workflow regression seed
- no EPIC-126 hardening or broadened product scope folded into the first-demo runbook

## Source files changed
- `src/onetruth/application/services/logistics_local_demo.py`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/route_specs/workflow_runs.py`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/application/projections/workspace_graphs/live_dispatch.py`
- `src/onetruth/application/projections/workspace_graphs/registry.py`
- `src/onetruth/api/routes/logistics_story.py`
- `scripts/run_logistics_local_demo.py`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workflowRunsRepository.ts`
- `frontend/src/lib/workspace/taskLabels.ts`
- `frontend/src/test/api/contractState.ts`
- `frontend/src/test/api/handlers.ts`
- `fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml`
- `fixtures/logistics/local_demo_upload_pack/README.md`
- `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml`
- `docs/ops/runbooks/logistics_local_demo_weekly_first.md`
- `tests/runtime/scenarios/test_weekly_first_local_demo_seed.py`
- `tests/runtime/api/test_logistics_weekly_first_local_demo_story_endpoint.py`
- `tests/runtime/contracts/test_logistics_local_demo_seed_script.py`
- `tests/runtime/api/test_logistics_local_demo_smoke_api.py`
- `frontend/src/pages/logisticsDemoPage.test.tsx`
- `frontend/src/lib/api/onetruthApi.logisticsStory.test.ts`

## Verification
- `PYTHONPATH=src:.venv/lib/python3.9/site-packages python3.11 -m pytest tests/runtime/test_logistics_handoff_runtime.py tests/runtime/scenarios/test_weekly_first_local_demo_seed.py tests/runtime/api/test_logistics_weekly_first_local_demo_story_endpoint.py tests/runtime/contracts/test_logistics_local_demo_seed_script.py tests/runtime/api/test_logistics_local_demo_smoke_api.py -q`
- `cd frontend && npm run test:run -- src/pages/logisticsDemoPage.test.tsx src/lib/api/onetruthApi.logisticsStory.test.ts`
- `PYTHONPATH=src python3.11 scripts/validate_repo.py`
- `python3.11 scripts/run_logistics_local_demo.py --db-url sqlite:///.tmp/local-demo-check.db --output-json .tmp/local-demo-check.json`

## Outcome
- The repo now has a dedicated weekly-first local demo seed, launcher script, and bounded cross-workflow upload pack instead of relying on the fully precomposed story seed as the default operator walkthrough.
- `/demo/logistics` now starts from weekly/reporting workspaces and surfaces `Prepare service day` until a live run exists, keeping workpages contextual instead of primary.
- The story shell and runtime tests now truthfully support a partial-progress first-demo posture: prior reporting feedback exists at seed time, weekly and reporting runs are open, and live dispatch does not exist until explicitly prepared.
- The first local demo runbook now gives exact startup commands, upload files, and click order, and it explicitly points follow-up feedback into `TASK-0157` instead of widening into EPIC-126 hardening.
