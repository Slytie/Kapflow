# WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md

## Summary

This dated note captures the 2026-04-06 review packet findings for the minimal workpage demo-enablement tranche.

The repo is close to being demoable, but the imported packet diagnosis now needs correction: supported-env verification no longer reproduces the Stage04 smoke failure, and the remaining gap is honest reporting-intake dependency classification plus operator tooling.

## Concrete findings

### 1. The scaffold seed is not workpage-ready by itself

`src/onetruth/application/services/logistics_local_demo.py` returns story/workspace URLs and creates run/task shells, but it does not materialize:

- a `planning.draft_weekly_schedule.workbook` artifact for `schedule-v0`,
- a driver-preferences snapshot for `driver-preferences-v0`.

### 2. The missing prep steps currently live in a smoke test

`tests/runtime/api/test_logistics_local_demo_smoke_api.py` performs the missing runtime steps manually.

That is good evidence but poor operator ergonomics.

### 3. The packet's Stage04 smoke diagnosis is stale

Current supported-env verification in a clean Python `3.11` install is green for:

- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py`
- `tests/runtime/api/test_logistics_local_demo_smoke_api.py`
- `tests/unit/test_dispatch_reporting_workbook.py`

The remaining truth gap is that a partial Python `3.11` environment without `openpyxl` currently causes reporting intake to fail as `unsupported_eos_workbook_shape` instead of an explicit missing-runtime-dependency error.

### 4. The canonical read-side workpage surfaces are otherwise in good shape

Representative schedule, route-demand, and driver-preferences workpage contract tests still provide a stable read-side surface, so the demo problem is not that the workpages themselves are absent.

## Implication

The smallest truthful demo-enablement tranche is:

1. correct the stale Stage04 diagnosis and reporting-intake dependency classification,
2. extract a one-command deterministic prep path from the implicit smoke procedure,
3. document the startup flow and canonical URLs.
