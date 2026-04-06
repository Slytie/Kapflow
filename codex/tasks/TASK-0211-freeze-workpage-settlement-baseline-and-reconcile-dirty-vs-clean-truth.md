---
id: TASK-0211
epic: EPIC-132
title: "Freeze the workpage settlement baseline and reconcile historical findings against live repo truth"
status: DONE
owners: ["backend", "qa"]
reviewers: ["architect"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-132.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
The 2026-04-05 settlement packet captured real instability, but the live repo has moved since then. This task must separate:
- historical findings that are already resolved in the current checkout,
- genuine settlement gaps that still remain in supported environments,
- and architectural debts that are real but belong to EPIC-133 rather than EPIC-132.

## Objective
Produce a clean settlement baseline for the workpage tranche. After this task, the team should know exactly:
- which packet findings are now historical only,
- which items still belong to EPIC-132,
- and which items are explicitly deferred to EPIC-133.

## Non-goals
- No new product behavior.
- No broad architectural refactor.
- No shared smoke gate yet.
- No client/server action-model refactor.
- No history-query migration or demo-shell convergence work.

## Source files to read first
- `git status --short`
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/epics/EPIC-126.md`
- `docs/planning/epics/EPIC-132.md`
- `codex/context/EPIC-131.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`
- the high-signal workpage files called out in the EPIC-132 context pack

## Classification table
| Bucket | Items | Expected handling in this task |
| --- | --- | --- |
| Already resolved in live repo | clean `git status`, restored `uuid4` import, EOD create idempotency scoped to `reporting.upd_draft.workbook`, Node 20 baseline encoded in repo truth | record as historical findings from 2026-04-05 and do not reopen them as active regressions |
| Still open for EPIC-132 | any supported-env mutation failures, stale docs/fixtures/snapshots that still misstate the canonical-only posture, missing supported-env install truth needed to classify a failure honestly | keep in the settlement tranche and fix only if they block a truthful clean baseline |
| Explicitly deferred to EPIC-133 | client `subject_link`, client-built history rails, inline demo mutation logic, file decomposition/guardrails | call out explicitly as live debt, but do not implement them in this task |

## Source files to change
- settlement planning docs and context packs imported by this task
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- only the smallest additional workpage/backend/test file if a genuine supported-env regression still blocks an unambiguous baseline

## Plan
1. Import the settlement plan, epic docs, context packs, and task briefs into repo truth.
2. Reconcile the 2026-04-05 packet findings against the live repo before changing behavior.
3. Record the classification above so the repo does not keep carrying ambiguous “maybe still broken” history.
4. Run supported-environment mutation spot checks.
5. If a real committed regression still remains, land only the smallest restorative fix needed to make the baseline truthful, then stop.

## Verification
- clean `git status`
- supported-environment spot checks for:
  - EOD create replay
  - EOD submit replay
  - schedule submit replay
  - route-demand save plus single refresh-task behavior
  - driver-preferences submit successor behavior
  - weekly publish happy path and drift fail-closed path

## Acceptance criteria
- The workpage tranche has a clearly identified clean settlement baseline.
- The repo records which 2026-04-05 findings are historical versus still open.
- No broken workaround or ambiguous WIP state remains hidden in active repo truth.
- The next settlement tasks can start from one stable baseline instead of competing narratives.

## Execution notes
- Reconciled historical findings against the live repo:
  - `git status --short` was clean before this task.
  - `src/onetruth/application/handlers/workpages.py` already restored the `uuid4` import.
  - `tests/runtime/api/test_workpages_artifact_eod_contract.py::test_canonical_eod_draft_create_replays_idempotently_without_duplicate_artifacts` already scopes to `reporting.upd_draft.workbook`.
  - Node 20 install truth is already encoded in `.nvmrc`, `frontend/package.json`, and active docs.
- Spot checks run successfully in the existing Python 3.11 / Node 20 workspace:
  - EOD create replay
  - schedule submit replay
  - route-demand drift/save single refresh-task behavior
  - driver-preferences submit successor behavior
  - weekly publish happy path and drift fail-closed path
  - frontend workpage repository/route/EOD page spot check
- Clean-environment bootstrap was attempted with `/tmp/onetruth-py311-task0211`, but `python -m pip install -e ".[api,dev]"` could not complete in this workspace because package-index access was unavailable.
- The remaining locally reproducible failure is `tests/runtime/api/test_workpages_artifact_eod_contract.py::test_submit_artifact_workpage_replays_idempotently_without_duplicate_versions`, which still fails with `ModuleNotFoundError` when `openpyxl` is absent from the active Python 3.11 environment. Treat that as still-open EPIC-132 verification/bootstrap work, not proof of a new code regression landed in this task.
