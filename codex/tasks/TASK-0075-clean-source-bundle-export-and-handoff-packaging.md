---
id: TASK-0075
epic: EPIC-080
title: "Clean source-bundle export and handoff packaging"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0071"]
risk: low
context_packs: ["EPIC-080"]
patterns: ["PATTERN-009", "PATTERN-003"]
---

## Context
Recent handoffs included workstation-local material and runtime evidence roots that made source-oriented review harder than it needed to be.

## Objective
Add a repeatable clean source-bundle export path that packages repo source from the current working tree while excluding workstation/runtime clutter by default.

## Non-goals
- No runtime/business-semantics changes.
- No cleanup/removal pass across intentionally versioned docs or fixtures.
- No redesign of existing runtime workspace inspection bundle behavior.

## Source Files Changed
- `scripts/export_clean_source_bundle.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `Makefile`
- `README.md`
- `docs/planning/WORKFLOW_WORKSPACE_DEMO_AND_GRAPH.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0075-clean-source-bundle-export-and-handoff-packaging.md`

## Verification Run
- `python3 scripts/validate_repo.py --schemas-only` - passed
- `pytest tests/contract/test_clean_source_bundle_export.py -vv` - passed
- `make clean-source-bundle` - passed
- `unzip -l .tmp/companyos-clean-source-bundle.zip | sed -n '1,60p'` - inspected archive layout
- zip inclusion/exclusion inspection via `zipinfo` + Python stdlib checks - passed; verified inclusion of source files and exclusion of `.git`, `.venv`, `node_modules`, `frontend/dist`, `.tmp`, `.pytest_cache`, `.idea`, local env files, local DBs, and runtime evidence roots

## Acceptance Criteria Coverage
- Added a one-command clean source bundle path via `make clean-source-bundle`.
- Added repo-native exporter `scripts/export_clean_source_bundle.py` with explicit clutter exclusions for workstation/editor/env/database/runtime evidence paths.
- Default export mode captures the current working-tree source snapshot (tracked files plus non-ignored untracked source files) so handoffs can include in-progress repo-native changes without zipping the whole working tree.
- Added `--tracked-only` for strictly git-tracked exports.
- Updated README and workspace/export docs so repo handoffs use the clean source bundle path while runtime inspection bundles continue to use `scripts/export_run_workspace_bundle.py`.
- Added contract coverage proving the exporter excludes clutter and that `--tracked-only` suppresses untracked source files.

## Completion Notes (2026-03-13)
- Real-repo verification surfaced one additional local runtime evidence root, `.onetruth_artifacts/`, so the exporter now excludes that path alongside `artifacts/`.
- The exporter intentionally uses the working tree rather than `git archive` so local repo-native changes are preserved in handoff bundles without dragging along ignored workstation state.
- This task did not remove tracked clutter from source control; it only ensured the handoff/export path stays clean and reviewable by default.
