# Prompt for TASK-0076 — Restore board stability and classify primary vs legacy query surfaces

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Restore the failing legacy schedule-only board seam with the smallest honest patch, and make the primary-vs-legacy surface classification explicit.

## Prerequisites
- Depends on TASK-0064. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0075. Do not start coding if that dependency is incomplete or semantically unresolved.

## Non-negotiable constraints
- Logistics story / `/demo/logistics` remains the primary product surface.
- Schedule-only board/workspace routes remain legacy/internal regression seams.
- No shared read-model package extraction in this task.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0076`: **Restore board stability and classify primary vs legacy query surfaces**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/pointers.py`
- `src/onetruth/api/routes/logistics_story.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`

### What to figure out before coding
- Confirm the exact `query_pointers(...)` signature drift causing `GET /api/v1/board/schedule-planning` to 500.
- Check whether any other route-to-route imports are implicated, but defer broader extraction work to TASK-0083.
- Decide the minimum docs/test wording needed to mark logistics story surfaces as primary and schedule-only board/workspace as legacy regression.

### Red-team checks
- Do not accidentally re-center architecture work on the schedule-only board just because the regression is loud.
- Do not hide the layering smell; record it explicitly as a follow-on for TASK-0083.
- Keep endpoint shape stable; this is a stability patch, not a contract redesign.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0076` has been reviewed and approved.

You are resuming `TASK-0076` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/pointers.py`
- `src/onetruth/api/routes/logistics_story.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/api/routes/board.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md`

### Verification to run
- `PYTHONPATH=src pytest tests/runtime/api/test_board_retry_stability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_board_schedule_planning_contract.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
