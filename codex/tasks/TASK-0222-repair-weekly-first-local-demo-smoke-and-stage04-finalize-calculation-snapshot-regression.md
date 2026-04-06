---
id: TASK-0222
epic: EPIC-134
title: "Correct the weekly-first local demo smoke diagnosis and reporting-intake runtime-dependency truth"
status: TODO
owners: ["backend"]
reviewers: ["qa"]
depends_on: ["TASK-0221"]
risk: medium
context_packs:
  - "codex/context/EPIC-134.md"
  - "codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md"
patterns: ["one-truth", "fail-closed"]
---

## Why
The imported 2026-04-06 packet diagnosed the weekly-first local demo smoke as a Stage04 finalize regression, but that diagnosis is stale unless it reproduces in the supported environment.

Current repo-grounded verification in a clean Python `3.11` install with `python3.11 -m pip install -e ".[api,dev]"` shows:

- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py` is green,
- `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py` is green,
- `tests/runtime/api/test_logistics_local_demo_smoke_api.py` is green,
- `tests/unit/test_dispatch_reporting_workbook.py` is green.

The remaining problem is dependency honesty: in a partial Python `3.11` environment without `openpyxl`, dispatch-reporting intake currently fails as `unsupported_eos_workbook_shape` instead of an explicit missing runtime dependency.

## Scope
- verify the supported-env baseline before changing behavior and keep Stage04 out of scope unless that repro goes red again
- classify missing reporting workbook runtime support as `runtime_dependency_missing` with `dependency: "openpyxl"`
- keep `unsupported_eos_workbook_shape` for genuine parse/shape mismatches once dependencies are present
- centralize the current repo-supported reporting workbook sample used by the reporting happy path and local demo smoke
- update repo memory so EPIC-134 no longer advertises Stage04 finalize repair as the active blocker
- keep the repair minimal; do not widen product scope

## Out of scope
- redesigning Stage04 agent behavior
- changing workpage contracts
- adding new demo features

## Repo-grounded failure to fix
Observed local partial-env failure shape:
- `python3.11` in this workspace can be missing `openpyxl`
- when that happens, dispatch-reporting intake completion currently returns `unsupported_eos_workbook_shape`
- the misclassification path enters `build_dispatch_reporting_artifacts(...)` through Stage01 reporting intake completion in `src/onetruth/application/handlers/human_tasks.py`

## Likely touch points
- `src/onetruth/application/services/dispatch_reporting_workbook.py`
- `src/onetruth/application/services/dispatch_reporting_build.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/api/errors.py`
- `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py`
- `tests/runtime/api/test_logistics_local_demo_smoke_api.py`
- `tests/unit/test_dispatch_reporting_workbook.py`
- EPIC-134 docs/context files that still name the stale Stage04 diagnosis

## Verification
- `python3.11 -m pip install -e ".[api,dev]"`
- `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_dispatch_reporting_workbook.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/api/test_logistics_local_demo_smoke_api.py`
- `make PYTHON=python3.11 workpage-mutation-smoke`

## Outcome
The repo no longer misclassifies missing reporting workbook runtime support as a bad workbook shape, and EPIC-134 memory accurately treats Stage04 as a supported-env scope gate rather than the active blocker.
