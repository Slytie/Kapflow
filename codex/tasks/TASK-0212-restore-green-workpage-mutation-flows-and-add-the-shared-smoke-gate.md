---
id: TASK-0212
epic: EPIC-132
title: "Restore green workpage mutation flows and add the shared smoke gate"
status: DONE
owners: ["backend", "qa"]
reviewers: ["architect"]
depends_on: ["TASK-0211"]
risk: high
context_packs:
  - "codex/context/EPIC-132.md"
  - "codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
The workpage layer now uses shared helper seams for artifact creation/submission. That is architecturally useful, but it means one helper regression can break multiple public write paths.

There may also still be committed or supported-environment test-truth gaps after the baseline reconciliation in TASK-0211.

## Objective
Restore trustworthy mutation behavior for the current public workpage family and protect it with a deliberately small smoke suite that always runs.

## Non-goals
- No new workpage features.
- No server-authored action model yet.
- No demo-shell refactor yet.

## Source files to read first
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/workpages.py`
- `tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `tests/runtime/api/test_workpages_artifact_schedule_contract.py`
- `tests/runtime/api/test_workpages_route_demand_contract.py`
- `tests/runtime/api/test_workpages_driver_preferences_contract.py`
- `tests/runtime/api/test_weekly_publish_loop_api.py`

## Source files to change
- backend workpage handlers/routes/helpers
- targeted runtime tests and any tiny helper tests needed for the smoke gate

## Plan
1. Reproduce the workbook unit and EOD submit replay behavior in a clean Python 3.11 install with `.[api,dev]`.
2. If that supported install still shows a real regression, fix only the smallest write-path seam required to restore truthful behavior.
3. Add a narrow public workpage mutation smoke gate covering:
   - EOD create + replay,
   - EOD submit + replay,
   - schedule submit + replay,
   - route-demand submit + replay,
   - driver-preferences create/submit + replay,
   - weekly publish happy path and drift fail-closed path.
4. Add a fail-fast dependency-readiness probe for the smoke gate so missing runtime imports like `openpyxl` surface clearly before the API tests run.
5. Wire the smoke gate into `make`, `ci-fast-backend`, and the main required CI matrix.

## Verification
- clean Python `3.11` env with `python -m pip install -e ".[api,dev]"`
- `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_dispatch_reporting_workbook.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py::test_submit_artifact_workpage_replays_idempotently_without_duplicate_versions`
- `make PYTHON=python3.11 workpage-mutation-smoke`
- targeted workpage runtime/API regression suites
- `PYTHONPATH=src python3.11 -m pytest -q tests/contract/test_repo_automation_truth.py`

## Acceptance criteria
- Public workpage mutation flows are green and trustworthy again.
- The test layer asserts the correct semantic quantities.
- A future one-line helper regression in shared workpage mutation code is caught by the smoke gate.

## Execution notes
- Clean-install verification in `/tmp/onetruth-py311-task0212` succeeded with `python -m pip install -e ".[api,dev]"`.
- In that supported Python `3.11` environment, both `tests/unit/test_dispatch_reporting_workbook.py` and `tests/runtime/api/test_workpages_artifact_eod_contract.py::test_submit_artifact_workpage_replays_idempotently_without_duplicate_versions` passed without any runtime code change.
- Because the supported-env reproduction was green, this task did not change `src/onetruth/application/services/dispatch_reporting_workbook.py` or `src/onetruth/application/handlers/workpages.py`.
- The task instead landed a dedicated smoke module, a fail-fast runtime dependency probe in `make workpage-mutation-smoke`, CI wiring in `.github/workflows/main.yml`, and the matching repo-automation/doc-truth updates.
