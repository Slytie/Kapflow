# Prompt for TASK-0083 — Extract the shared read-model seam and forbid route-to-route imports

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Extract the genuinely shared read-model seam and add a fitness rule forbidding route-to-route imports, so board/story composition stops depending on route internals.

## Prerequisites
- Depends on TASK-0076. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0081. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[HTTP\ adapter\ layer \perp internal\ read\_model\ layer\]

## Non-negotiable constraints
- No route module may import another route module after this task.
- The extracted seam should be as small as possible.
- Legacy schedule-only board regression and primary logistics story surfaces must both stay green.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0083`: **Extract the shared read-model seam and forbid route-to-route imports**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0083-shared-read-model-seam-and-route-boundary-fitness.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- codex/context/EPIC-040.md
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/logistics_story.py`
- `src/onetruth/api/routes/*.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`

### What to figure out before coding
- Enumerate the current route-to-route imports and identify which `query_*` helpers are genuinely shared.
- Choose the smallest honest home for the extracted seam (`application/read_models` or `api/queries`).
- Decide whether any tiny DTO/filter types are needed locally to prevent signature drift without spilling across the whole API shell.

### Red-team checks
- Do not do a broad framework migration or route-registry rewrite here.
- Do not create a speculative abstraction for every route just because a few helpers are shared.
- Keep board and logistics story endpoint response shapes stable.

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

Use this section only **after** the Ask-mode plan for `TASK-0083` has been reviewed and approved.

You are resuming `TASK-0083` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0083-shared-read-model-seam-and-route-boundary-fitness.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- codex/context/EPIC-040.md
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/logistics_story.py`
- `src/onetruth/api/routes/*.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/application/read_models/` or `src/onetruth/api/queries/` (new)
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/logistics_story.py`
- relevant route files whose `query_*` helpers move
- `tests/contract/test_route_layer_boundaries.py` (new)
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0083-shared-read-model-seam-and-route-boundary-fitness.md`

### Verification to run
- `pytest tests/contract/test_route_layer_boundaries.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_board_retry_stability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_logistics_three_workflow_story_endpoint.py -q`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
