---
id: TASK-0646
epic: EPIC-139
title: EPIC-139 redo task-by-task reclose ledger
status: DONE
completed_at: "2026-06-04T11:49:41Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0645"]
risk: high
context_packs: ["codex/context/EPIC-139.md"]
patterns: ["EPIC-139 redo reclose ledger", "task evidence reconciliation"]
---

# TASK-0646 - EPIC-139 Redo: Task-By-Task Reclose Ledger

## Why

The EPIC-139 redo package required a final task-by-task reclose pass after supported-environment acceptance. The goal is to prevent old DONE rows from becoming a vague green backdrop after the State B false-green finding.

## Scope

Add a repo-native reclose ledger that maps every original EPIC-139 DONE or reconciled row to fresh neutral-default evidence, explicit logistics activation evidence, docs/test-lane evidence, or historical-alias reconciliation.

## Out of scope

- Runtime behavior changes.
- New public HTTP routes, schemas, or plugin framework shape.
- Rewriting old EPIC-139 closeouts unless a concrete contradiction is found.
- Activating CAPEX runtime/product behavior.

## Verification

- `python3.11 -m pytest -q tests/contract/test_epic139_redo_reclose_matrix.py`
- `python3.11 -m pytest -q tests/contract/test_capex_epic_progress_data.py tests/contract/test_capex_v5_reconciliation.py tests/contract/test_platform_logistics_test_split.py`
- `make PYTHON=python3.11 logistics-regression-tests`
- `python3.11 -m pytest -q tests/unit/test_approval_response_hooks.py tests/unit/test_workpage_descriptor_registry.py tests/unit/test_workpage_domain_registry.py`
- `python3.11 scripts/run_capex_invariant_audit.py --output-root /private/tmp/kapflow-epic139-task0646-audit --json`
- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`
- `python3.11 scripts/validate_repo.py`
- `npm run test:run -- src/pages/capexEpicProgressPage.test.tsx` from `frontend/`
- `git diff --check`

## Acceptance criteria

- `docs/planning/EPIC139_REDO_RECLOSE_MATRIX.md` covers every original EPIC-139 source row, the `TASK-0576` historical alias, and redo tasks `TASK-0643` through `TASK-0646`.
- Every matrix row has stable columns: `task_id`, `source_row`, `theme`, `redo_action`, `reclose_status`, `evidence_command`, `evidence_refs`, and `notes`.
- Reclose statuses are limited to `reclosed`, `historical_alias`, and `redo_task`.
- Matrix evidence references point at existing task files, docs, or tests.
- Contract tests fail if the matrix loses coverage or leaves any row unproven.

## Source row mapping

- Source task ID: `E139-REDO-008`
- Source priority: `P1`
- Source area: `task-by-task-reclose`

## Closeout evidence

- Added `docs/planning/EPIC139_REDO_RECLOSE_MATRIX.md` as the repo-native task-by-task reclose ledger.
- Added contract coverage that verifies required row coverage, stable column shape, allowed statuses, existing evidence references, and `TASK-0576` historical-alias preservation.
- Regenerated CAPEX progress data so TASK-0646 is represented under EPIC-139.
- Waivers: none.
