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

Current repo status: `TASK-0086` is complete via a first bounded hotspot extraction that moved the approvals command family into `src/onetruth/application/handlers/approvals.py` behind compatibility wrappers in `workflow_task_lifecycle.py`.
