# EPIC-040 - Orchestrator core (runs pinned, WAIT, bounded exception handling)

## Summary
Define and later implement the minimal runtime object model and state semantics for Stage 4.

## Why this epic exists (risk retired)
Without a clear runtime model, the merger risks separate business-run and agent-run systems.

## Scope
### In scope
- workflow run
- task run
- execution session as a facet, not a peer universe
- bounded exception handling
- stale / wait / retry / no-progress states
- runtime object schemas that precede implementation planning
- concrete runtime bootstrap and first code slice

### Out of scope
- generalized multi-level study/program orchestration

## Dependencies
- EPIC-020
- EPIC-025
- EPIC-030

## Key decisions / constraints
- transcripts are evidence, not state
- Schedule Planning Stage07 is a bounded exception loop inside the same workflow-run context
- runtime work should instantiate the chosen package layout and persistence model rather than re-deciding them ad hoc
- public mutation retries belong to the canonical command boundary via scoped receipts, while raw event append idempotency remains an internal event-store concern

## Recommended pattern cards (read cards first)
- `PATTERN-001`
- `PATTERN-002`
- `PATTERN-003`
- `PATTERN-004`

Context pack: `codex/context/EPIC-040.md`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

## Deliverables
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `schemas/runtime/*`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`

## Tasks
- TASK-0011
- TASK-0023
- TASK-0028
- TASK-0036
- TASK-0082
- TASK-0086
- TASK-0092
- TASK-0093

Current repo status: `TASK-0086` is complete via a first bounded hotspot extraction that moved the approvals command family into `src/onetruth/application/handlers/approvals.py` behind compatibility wrappers in `workflow_task_lifecycle.py`. `TASK-0092` is now also complete: the extracted approvals family depends on a neutral `src/onetruth/application/handlers/_shared/command_boundary.py` seam for shared command-boundary helpers, so the compatibility cycle back into `workflow_task_lifecycle.py` is retired without changing approval behavior. `TASK-0093` is now also complete: the human-task mutation family lives in `src/onetruth/application/handlers/human_tasks.py`, confirm-review support helpers no longer live only in the legacy hotspot, and existing callers still route through thin `workflow_task_lifecycle.py` wrappers. `TASK-0102` is now also complete: neutral read surfaces live in `src/onetruth/application/read_commands/`, API/query/service layers consume `CommandError` from the shared command-boundary seam instead of the legacy hotspot, and contract coverage forbids those shared read/error imports from drifting back. `TASK-0103` is now also complete: the flag and Stage07 issue-loop mutation family lives in `src/onetruth/application/handlers/flags.py`, direct API/CLI/service callers no longer import those mutations from the legacy hotspot, and compatibility plus runtime/security coverage keep the extraction structural.

Planned next tranche in this epic:
- The orchestrator objective for the next tranche is no longer semantics hardening; it is centrality reduction without changing runtime truth.

## Queued Tasks
