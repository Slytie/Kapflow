---
id: TASK-0212
epic: EPIC-132
title: "Restore green workpage mutation flows and add the shared smoke gate"
status: TODO
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
1. Fix any known shared-helper write regression that remains after supported-env verification.
2. Reconcile idempotency assertions so tests count the correct semantic object.
3. Add a narrow public workpage mutation smoke gate covering at least:
   - EOD create + replay,
   - EOD submit + replay,
   - schedule submit + replay,
   - route-demand submit + replay,
   - driver-preferences create/submit + replay,
   - weekly publish happy path and drift fail-closed path.
4. Keep the smoke gate small enough to run on every change touching shared workpage mutation helpers.

## Verification
- targeted backend runtime/API tests
- the new smoke gate runs green from a clean checkout
- no duplicate truth objects are created by replay in the protected flows

## Acceptance criteria
- Public workpage mutation flows are green and trustworthy again.
- The test layer asserts the correct semantic quantities.
- A future one-line helper regression in shared workpage mutation code is caught by the smoke gate.
