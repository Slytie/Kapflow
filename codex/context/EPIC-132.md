# EPIC-132 Context Pack - Workpage reliability settlement and repo-truth closeout

Purpose:
- Finish the post-EPIC-131 settlement work needed so the repo has a clean, trustworthy workpage baseline.
- Do not use this epic to widen product scope.

## Non-negotiable invariants
- Public workpage posture remains canonical-only.
- Workpages remain derived surfaces over canonical workflow/task/artifact/pointer truth.
- Drafts and accepted artifacts remain distinct.
- Route-demand, schedule, EOD, and driver-preferences stay separate truth objects/surfaces.
- A clean checkout with a green targeted mutation suite is the stop line for this epic.

## Authoritative docs
- `docs/planning/epics/EPIC-132.md`
- `docs/planning/WORKPAGES_POST_EPIC131_STABILIZATION_AND_SETTLEMENT_PLAN.md`
- `codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`
- `docs/planning/epics/EPIC-131.md`
- `codex/context/EPIC-131.md`

## Start conditions
You are no longer starting from the exact dirty 2026-04-05 snapshot described in the packet.

Current expected start posture for `TASK-0211`:
- the live repo should be checked first,
- historical dirty-tree findings should be treated as dated evidence,
- the first task is to freeze the current clean baseline and classify remaining gaps,
- supported-environment verification is the only authoritative basis for deciding whether a regression is still open.

## High-signal source files to inspect immediately
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/services/workpage_descriptors.py`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/pages/DispatchReportWorkpagePage.tsx`
- `tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `tests/runtime/api/test_workpages_artifact_schedule_contract.py`
- `tests/runtime/api/test_workpages_route_demand_contract.py`
- `tests/runtime/api/test_workpages_driver_preferences_contract.py`
- `tests/runtime/api/test_weekly_publish_loop_api.py`
- active docs/fixtures touched by the settlement plan

## Known concrete issues to classify rather than assume
- Historical dirty-tree regression: missing `uuid4` import in `_create_workbook_artifact_version(...)`.
- Historical committed test-truth gap: EOD idempotency replay assertion counted whole-run artifacts instead of the draft artifact family.
- Live architectural debt that still appears current: client `subject_link`, client-built history rails, inline demo mutation logic, concentration files.
- Environment truth requirement: Python `3.11` plus installed project deps, and Node `20` plus clean install, must be used when classifying failures.

## Verification posture
Before declaring EPIC-132 complete, verify at least:
- targeted backend workpage/runtime tests,
- a small write-path smoke gate,
- targeted frontend workpage tests from a clean Node 20 install,
- clean `git status` in the settled branch.

## Stop line
Do not move on to the deeper hardening in EPIC-133 until this epic leaves the repo in a clean, green, non-ambiguous state.
