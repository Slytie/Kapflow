> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# LOGISTICS_WORKPAGE_DEMO_ENABLEMENT_PLAN.md

## Purpose

Enable a reliable, low-overhead demo of the already-landed Workpages v1 changes without reopening product scope or introducing demo-only runtime behavior.

The demo should validate the canonical workpage surfaces that now matter:

- `schedule-v0`
- `route-demand-v0`
- `driver-preferences-v0`
- `eod-v0`

under the canonical public route family:

- `/runs/:workflowRunId/workpages/*`

## First-principles model

Let:

- `S_seed` be the scaffolded weekly-first local demo state from `seed_weekly_first_logistics_local_demo(...)`
- `T_demo` be a deterministic, idempotent preparation operator that materializes the minimum canonical artifacts needed for workpage validation
- `S_demo = T_demo(S_seed)`
- `W_k = Π_k(S_demo)` be the server-authored workpage projection for workpage kind `k`

The demo problem is not to invent a new product posture. The demo problem is to construct `S_demo` cheaply and truthfully so that the existing canonical projections can be exercised.

Therefore the preferred solution is:

1. keep the public runtime and routing model unchanged,
2. keep the story shell as optional narrative context,
3. add a tiny deterministic prep step that materializes canonical truth objects,
4. validate the demo on canonical workpage routes.

## Why this should stay small

The repo already has most of the needed substrate:

- `scripts/run_logistics_local_demo.py` seeds the weekly/reporting scaffold,
- weekly Stage04 deterministic build logic already exists,
- route-demand and driver-preferences workpages already exist,
- the canonical workpage routes already exist,
- runtime tests already validate most read-side workpage contracts.

The main missing pieces are operational, not architectural:

1. repo memory still points at a stale Stage04-local-demo diagnosis instead of the real remaining reporting-intake dependency-honesty gap,
2. the full workpage-ready state still lives implicitly in a smoke test rather than a user-facing prep script,
3. there is no concise runbook that tells an operator how to start the services, prepare the canonical workpage state, and open the right routes.

## Observed repo-grounded gaps

### 1. Existing scaffold seed is not enough for workpage validation

`seed_weekly_first_logistics_local_demo(...)` creates:

- one current weekly run,
- one current reporting run,
- one prior reporting-feedback run,
- a story-shell URL,
- workspace URLs,
- task shells,
- prior reporting final packet + pointer + notify-only handoff.

It does not itself create the weekly draft schedule or driver-preferences snapshot needed to exercise the new workpages.

### 2. The full prep procedure currently lives in a smoke test

`tests/runtime/api/test_logistics_local_demo_smoke_api.py` performs the missing steps manually:

- claim weekly intake,
- upload weekly inputs,
- complete intake,
- run Stage04,
- complete build,
- confirm review,
- approve publish,
- prepare live dispatch,
- continue reporting/live loops.

That is useful as an oracle, but it is not a user-facing demo-prep surface.

### 3. The imported Stage04 diagnosis is stale; the remaining honesty gap is reporting intake classification

The 2026-04-06 review packet recorded a red weekly-first local demo smoke with a Stage04 finalize diagnosis.

Current repo-grounded verification in a clean Python `3.11` install with `python3.11 -m pip install -e ".[api,dev]"` shows:

- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py` is green,
- `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py` is green,
- `tests/runtime/api/test_logistics_local_demo_smoke_api.py` is green,
- `tests/unit/test_dispatch_reporting_workbook.py` is green.

The remaining problem is truthfulness, not Stage04 repair:

- a partial Python `3.11` environment without `openpyxl` currently causes dispatch-reporting intake to fail as `unsupported_eos_workbook_shape`,
- that missing-runtime-support case should instead surface as `runtime_dependency_missing`,
- the demo-enablement docs/task memory should stop advertising Stage04 finalize repair as the active blocker when supported-env verification no longer reproduces it.

## Constraints

### Hard constraints

- no new public product surfaces,
- no new demo-only truth system,
- no frontend-only semantic reconstruction,
- no requirement to build multi-week accepted-history seeding for the first demo,
- no large refactor of the story shell as part of this demo-enablement tranche.

### Preferred constraints

- prefer deterministic prep over model-dependent prep for the default demo path,
- the default demo-prep path should not require OpenAI,
- reuse existing canonical handlers/services/CLI commands,
- keep the prep operator idempotent,
- print canonical workpage URLs directly.

## Chosen demo posture

The demo should validate the workpage changes, not the OpenAI runtime.

So the smallest truthful demo-prep operator is:

1. run the existing weekly-first scaffold seed,
2. ensure the weekly run has canonical Stage04 input artifacts,
3. build the Stage04 outputs through the deterministic schedule-control path,
4. optionally create a driver-preferences snapshot,
5. print canonical workpage routes.

This is sufficient because the workpages consume canonical artifacts and projections, not the provenance of whether the draft schedule was produced by a model-assisted or deterministic orchestration step.

## Explicit non-goals for this demo tranche

- full multi-week accepted-history demo seeding,
- automated route-demand drift pre-seeding,
- automatic agentic rescheduling,
- replacing the story shell,
- adding a second product-specific demo mode.

## Recommended task order

1. `TASK-0221` - freeze the minimal demo boundary and recorded assumptions.
2. `TASK-0222` - correct the weekly-first local demo smoke diagnosis and reporting-intake runtime-dependency truth.
3. `TASK-0223` - add a one-command canonical workpage demo-prep script and JSON output.
4. `TASK-0224` - add the demo runbook and a regression that verifies the prep script and canonical URLs.

## Expected demo outputs

At the end of the prep script, the operator should have:

- one story-shell URL,
- one weekly workspace URL,
- one reporting workspace URL,
- canonical schedule landing URL,
- canonical route-demand landing URL,
- canonical driver-preferences landing URL,
- canonical schedule artifact URL for the seeded draft,
- canonical route-demand artifact URL,
- canonical driver-preferences artifact URL if a snapshot was created,
- optional EOD landing URL.

## Success criteria

The demo-enablement tranche is complete when:

1. the weekly-first local demo smoke is green again,
2. a single documented prep command can materialize workpage-ready state,
3. the script outputs canonical workpage URLs,
4. the runbook points operators to canonical routes instead of requiring manual state assembly,
5. no new public demo-only runtime path was introduced.
