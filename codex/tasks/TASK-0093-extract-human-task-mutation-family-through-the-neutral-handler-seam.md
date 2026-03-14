---
id: TASK-0093
epic: EPIC-040
title: "Extract the human-task mutation family through the neutral handler seam"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0092", "TASK-0080"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-050.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-003"]
---

## Context
Once the approvals compatibility cycle was retired, the next bounded hotspot move was the human-task mutation family: claim, complete, and confirm-review. These commands sit directly on the frozen capability lattice and the weekly/live logistics slice, so they needed a dedicated module without broadening into read-side task queries or artifact public commands.

## Objective
Extract the human-task mutation family into its own handler module behind the neutral command-boundary seam, while preserving frozen capability semantics and the existing runtime/API surface.

## Non-goals
- No extraction of read-side human-task queries in the same task.
- No extraction of public artifact commands, flags, or execute-service callers.
- No capability, Stage04 weekly/live, or Stage06 semantic changes.

## Source Files Changed
- `src/onetruth/application/handlers/_shared/command_boundary.py`
- `src/onetruth/application/handlers/_shared/artifact_effects.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `tests/unit/test_human_task_handler_compatibility.py`
- `tests/contract/test_handler_import_boundaries.py`
- `codex/tasks/TASK-0093-extract-human-task-mutation-family-through-the-neutral-handler-seam.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/context/EPIC-040.md`

## Generated / downstream artifacts impacted
- None beyond task-memory and extraction fitness coverage.

## Plan
1. Add compatibility and import-boundary tests that freeze legacy-wrapper vs extracted-handler parity.
2. Move only the human-task mutation family into a dedicated module behind the neutral command-boundary seam.
3. Extract the private confirm-review artifact-effect helper closure without moving public artifact commands.
4. Keep `workflow_task_lifecycle.py` import-compatible through thin lazy wrappers for existing callers.

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_human_task_handler_compatibility.py tests/contract/test_handler_import_boundaries.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_human_task_claim_via_api.py tests/runtime/api/test_human_task_complete_via_api.py tests/runtime/api/test_human_task_confirm_review_api.py tests/runtime/api/test_stage06_openai_review_sandbox_api.py tests/runtime/api/test_weekly_stage04_openai_agent_api.py tests/security/test_write_path_capability_enforcement.py tests/runtime/api/test_workspace_actionability.py`
- `python3 scripts/validate_repo.py --schemas-only`
- `PYTHONPYCACHEPREFIX=/tmp/pythoncache python3 -m compileall -q src tests scripts`

## Acceptance Criteria Coverage
- Human-task mutation commands now live outside `workflow_task_lifecycle.py` in a bounded `human_tasks.py` module.
- Existing callers still import through `workflow_task_lifecycle.py` compatibility wrappers without API/service churn.
- Import-boundary coverage fails if `human_tasks.py` or `_shared/*.py` re-import the legacy hotspot.
- Claim, complete, and confirm-review behavior stays parity-checked across legacy wrapper and extracted module surfaces.

## Completion Notes (2026-03-14)
- Added `src/onetruth/application/handlers/human_tasks.py` as the dedicated home for `claim_human_task_command`, `complete_human_task_command`, and `confirm_human_task_review_command`.
- Added `src/onetruth/application/handlers/_shared/artifact_effects.py` so confirm-review no longer needs to reach back into `workflow_task_lifecycle.py` for its private artifact-ingest support closure.
- Extended the neutral command-boundary seam with the small extra idempotency/time helpers the extracted mutation family still uses.
- Kept existing API/CLI/service callers stable by converting the legacy public mutation entries in `workflow_task_lifecycle.py` into thin lazy wrappers.
- Added compatibility coverage for legacy-vs-extracted human-task mutations and tightened the import-boundary fitness rule so the hotspot dependency does not creep back in.
