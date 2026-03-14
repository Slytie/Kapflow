---
id: TASK-0092
epic: EPIC-040
title: "Break the handler compatibility cycle with neutral command-boundary helpers"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0086", "TASK-0088"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-003"]
---

## Context
`TASK-0086` deliberately stopped after a small approvals-first extraction. That reduced hotspot risk, but it also left a bounded compatibility cycle: extracted handlers still relied on helper primitives that lived in `workflow_task_lifecycle.py`, and the legacy shim lazily delegated back into the extracted module.

This task retired that transitional cycle before more family extractions could spread the pattern.

## Objective
Move shared command-boundary helpers into a neutral module so extracted handler families no longer depend on `workflow_task_lifecycle.py` for their basic primitives.

## Non-goals
- No broad extraction of new command families.
- No semantic change to capability, Stage04, or execution-evidence behavior.
- No new “god helper” module; shared helpers remain narrow and boundary-focused.

## Source Files Changed
- `src/onetruth/application/handlers/_shared/__init__.py`
- `src/onetruth/application/handlers/_shared/command_boundary.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/handlers/approvals.py`
- `src/onetruth/cli/__main__.py`
- `tests/unit/test_command_receipts.py`
- `tests/contract/test_handler_import_boundaries.py`
- `codex/tasks/TASK-0092-break-handler-compatibility-cycle-with-neutral-command-boundary-helpers.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/context/EPIC-040.md`

## Generated / downstream artifacts impacted
- None beyond task-memory and import-boundary coverage.

## Plan
1. Add a contract test that forbids the extracted approvals family and shared helper seam from importing `workflow_task_lifecycle.py`.
2. Extract only the shared command-boundary helper cluster approvals already depended on.
3. Rewire approvals plus the known helper consumers (`cli/__main__.py`, `tests/unit/test_command_receipts.py`) to use the neutral seam.
4. Keep `workflow_task_lifecycle.py` import-compatible through re-exports while removing the local helper definitions that created the cycle.

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_approval_handler_compatibility.py tests/unit/test_command_receipts.py tests/contract/test_handler_import_boundaries.py`
- `python3 scripts/validate_repo.py --schemas-only`
- `PYTHONPYCACHEPREFIX=/tmp/pythoncache python3 -m compileall -q src tests scripts`

## Acceptance Criteria Coverage
- Extracted handler modules no longer depend on `workflow_task_lifecycle.py` for shared primitives.
- `workflow_task_lifecycle.py` remains import-compatible but is structurally thinner.
- Compatibility and import-boundary tests prove the transitional cycle is gone.

## Completion Notes (2026-03-14)
- Added `src/onetruth/application/handlers/_shared/command_boundary.py` as the neutral home for shared command-boundary helpers used by the extracted approvals family.
- Switched `approvals.py`, the CLI seed-corpus path, and command-receipt unit coverage off the legacy hotspot helper surface.
- Added contract coverage that fails if the extracted approvals family or shared helper seam re-imports `workflow_task_lifecycle.py`.
- Preserved approval behavior, receipts, and event payloads while keeping `workflow_task_lifecycle.py` import-compatible through re-exported helpers and lazy approval wrappers.
