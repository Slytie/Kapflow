# codex/tasks/

This folder contains task briefs. Treat each task as:
- the unit of work for a Codex run,
- the unit of durable memory for future runs,
- a place to record decisions, commands run, and outcomes.

## Naming
Use `TASK-XXXX-<slug>.md`

## Status values
- TODO
- IN_PROGRESS
- BLOCKED
- DONE

## Rules
- Keep scope small.
- Update the task file with source and generated-artifact impacts.
- Link the task to the relevant epic.
- Add `context_packs` and `patterns` when the task benefits from targeted context routing.
- Read pattern cards first; do not load long source notes unless the task directly touches that subsystem.
- If a task changes the authority chain, update the architecture docs before considering it done.
