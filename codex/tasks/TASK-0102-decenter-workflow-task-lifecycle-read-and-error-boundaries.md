---
id: TASK-0102
epic: EPIC-040
title: "Decenter workflow_task_lifecycle by extracting neutral read/error boundary surfaces"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0092", "TASK-0093"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-003"]
---

## Context
`workflow_task_lifecycle.py` is no longer the repo’s semantic contradiction hub, but it is still the dominant centrality hotspot. The most important remaining leak is not only mutation logic; it is the fact that API/dependency/query/service layers still import `CommandError` plus read/show/list helper surfaces directly from the legacy hotspot. That keeps unrelated layers coupled to the largest handler module and makes future extraction work harder than it should be.

This task retires that centrality leak before the next family extractions spread it further.

## Objective
Create neutral shared error/read boundary surfaces so API/query/service layers no longer depend on `workflow_task_lifecycle.py` for:
- `CommandError`
- workflow-run scoped lookup helpers
- show/list read commands currently imported from the legacy hotspot
- other non-mutation shared surfaces that should not require the full mutation hub

## Non-goals
- No behavior change to capability, trust-profile, or artifact semantics.
- No broad query-layer rewrite.
- No new runtime family extraction yet; this task creates the seam that later extractions will consume.
- No database/schema changes.

## Source files to read first
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/handlers/_shared/command_boundary.py`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/errors.py`
- `src/onetruth/api/queries/hitl_read_models.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `src/onetruth/application/services/realistic_schedule_planning_pilot.py`
- `tests/contract/test_handler_import_boundaries.py`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- `src/onetruth/application/handlers/_shared/command_boundary.py`
- one or more new neutral read-boundary modules under `src/onetruth/application/handlers/_shared/` or `src/onetruth/application/read_commands/`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/errors.py`
- `src/onetruth/api/queries/hitl_read_models.py`
- directly affected API route/service call sites that currently import read/error surfaces from the hotspot
- `tests/contract/test_handler_import_boundaries.py`
- new contract coverage for API/query/service import boundaries if needed

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.
- No generated runtime artifacts should change.

## Plan
1. Inventory every non-mutation import of `workflow_task_lifecycle.py`.
2. Move `CommandError` consumption to the neutral shared command-boundary seam.
3. Extract the smallest neutral read surface required by API/query/service layers.
4. Keep `workflow_task_lifecycle.py` import-compatible through thin re-exports/wrappers where needed.
5. Add contract tests forbidding API/query/service layers from importing the legacy hotspot for shared read/error surfaces.

## Verification
- `PYTHONPATH=src pytest -q tests/contract/test_handler_import_boundaries.py`
- targeted pytest for the API/query/service surfaces rewired by this task
- `python3 scripts/validate_repo.py --schemas-only`
- `PYTHONPYCACHEPREFIX=/tmp/pythoncache python3 -m compileall -q src tests scripts`

## Acceptance criteria
- API/query/service layers no longer import `CommandError` or neutral read helpers from `workflow_task_lifecycle.py`.
- `workflow_task_lifecycle.py` remains behavior-compatible but is less central.
- Import-boundary coverage makes the centrality leak difficult to reintroduce.

## Notes / decisions
The goal is not to eliminate the legacy hotspot in one pass. The goal is to stop using it as a shared library for unrelated layers.
- Implemented via a neutral `src/onetruth/application/read_commands/` seam for shared runtime reads, with API/query/service callers moved to that seam and `CommandError` moved to `src/onetruth/application/handlers/_shared/command_boundary.py`.
- `workflow_task_lifecycle.py` remains import-compatible through thin wrappers for the moved read surfaces.
