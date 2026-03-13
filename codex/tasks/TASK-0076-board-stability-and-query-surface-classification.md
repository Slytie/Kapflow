---
id: TASK-0076
epic: EPIC-080
title: "Restore board stability and classify primary vs legacy query surfaces"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0064", "TASK-0075"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-008", "PATTERN-009"]
---

## Context
`/demo/logistics` is now the primary product surface, but the legacy schedule-only board remains a regression/internal seam that still needs to stay honest and stable. The truth-alignment tranche starts by fixing that seam without letting it reclaim architectural priority.

## Objective
Restore the failing legacy board/query seam with the smallest honest patch, and make primary-vs-legacy surface classification explicit in tests and docs.

## Non-goals
- No read-model extraction or route-layer redesign in this task.
- No new board contract shape.
- No re-centering product posture on the schedule-only board.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/pointers.py`
- `src/onetruth/api/routes/logistics_story.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/api/routes/board.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md`

## Generated / downstream artifacts impacted
- Legacy board regression coverage only.
- No new generated artifacts are expected.

## Plan
1. Reproduce and diagnose the current schedule-only board failure.
2. Patch the narrow route/query seam without broad extraction.
3. Add the smallest tests proving the legacy board remains stable.
4. Update docs to classify logistics story surfaces as primary and schedule-only routes as legacy/internal.

## Verification
- `PYTHONPATH=src pytest tests/runtime/api/test_board_retry_stability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_board_schedule_planning_contract.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- `GET /api/v1/board/schedule-planning` no longer fails due to route/query signature drift.
- Board and logistics story response shapes stay stable.
- Docs and tests clearly mark logistics story surfaces as primary and schedule-only board/workspace routes as legacy/internal regression seams.
- Broader read-model extraction work is deferred explicitly to `TASK-0083`.

## Notes / decisions
- Ask mode first: confirm the exact failure and keep the repair bounded before touching code.
- Truth-alignment numbering source is the external zip prompt pack; `TASK-0076` is the board-stability task.

## Source Files Changed
- `src/onetruth/api/routes/board.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md`

## Verification Run
- `PYTHONPATH=src pytest tests/runtime/api/test_board_retry_stability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_board_schedule_planning_contract.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_logistics_three_workflow_story_endpoint.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance Criteria Coverage
- `GET /api/v1/board/schedule-planning` no longer fails due to pointer-query signature drift.
- Board payload shape remains unchanged while repeated reads stay stable.
- Docs and test intent explicitly preserve `/demo/logistics` and `GET /api/v1/stories/logistics-three-workflow` as the primary logistics surfaces.
- The route-to-route import seam is still visible and explicitly deferred to `TASK-0083`.

## Completion Notes
- The fix stayed bounded to the legacy board route: it now passes the full keyword set required by `query_pointers(...)` and reuses the same pointer filtering contract as other read surfaces.
- Board tests now identify themselves as legacy regression coverage so the product posture is harder to misread in future sessions.
- No shared read-model extraction was attempted here; that follow-on remains reserved for `TASK-0083`.
