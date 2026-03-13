---
id: TASK-0083
epic: EPIC-080
title: "Extract the shared read-model seam and forbid route-to-route imports"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0076", "TASK-0081"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007", "PATTERN-008", "PATTERN-009"]
---

## Context
The board and logistics story routes currently share query behavior through route-internal helpers. After the legacy board surface is stabilized and artifact ingress boundaries are clarified, the shared read seam can be extracted cleanly.

## Objective
Create the smallest honest shared read-model seam and add a fitness rule that forbids route-to-route imports, while keeping both the primary logistics story endpoint and the legacy board regression seam green.

## Non-goals
- No broad API framework migration.
- No speculative abstraction for every route.
- No response-shape redesign.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- `codex/context/EPIC-040.md`
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/logistics_story.py`
- `src/onetruth/api/routes/*.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `codex/context/EPIC-040.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/application/read_models/` or `src/onetruth/api/queries/`
- `src/onetruth/api/routes/board.py`
- `src/onetruth/api/routes/logistics_story.py`
- relevant route files whose shared `query_*` helpers move
- `tests/contract/test_route_layer_boundaries.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0083-shared-read-model-seam-and-route-boundary-fitness.md`

## Generated / downstream artifacts impacted
- Route-layer fitness coverage only.

## Plan
1. Enumerate current route-to-route imports and the genuinely shared query helpers.
2. Move only that shared seam into a neutral home.
3. Add a contract test forbidding route-to-route imports.
4. Keep board and logistics story endpoint contracts stable.

## Verification
- `pytest tests/contract/test_route_layer_boundaries.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_board_retry_stability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_logistics_three_workflow_story_endpoint.py -q`

## Acceptance criteria
- No route module imports another route module after this task.
- The extracted seam is minimal and honest.
- Primary logistics story and legacy board surfaces both stay green.
- Broader API-shell refactors remain out of scope.

## Notes / decisions
- Use the smallest shared home that prevents signature drift without creating a new framework.
