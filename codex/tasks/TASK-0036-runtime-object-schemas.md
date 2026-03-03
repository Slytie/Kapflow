---
id: TASK-0036
epic: EPIC-040
title: "Add runtime object schemas for canonical run/task/approval/execution objects"
status: DONE
owners:
- platform
reviewers:
- security
- ops
- qa
depends_on:
- TASK-0034
- TASK-0035
risk: high
context_packs:
- codex/context/EPIC-040.md
patterns:
- PATTERN-001
- PATTERN-002
- PATTERN-003
- PATTERN-004
---

## Context
The runtime object model exists narratively, but most canonical runtime objects still do not have machine-readable contracts. Implementation planning should not invent table/API shapes directly from prose.

## Objective
Add JSON Schemas for the canonical runtime objects so later implementation planning can serialize already-settled semantics.

## Non-goals
- Do not design tables or APIs yet.
- Do not encode the full transition algebra inside schema files.
- Do not introduce peer runtime objects that bypass the authority model.

## Source files to read first
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/human_task_semantics.md`
- `schemas/events/event_type_registry.yaml`
- `schemas/runtime/flag.schema.json`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `PATTERN-001`
- `PATTERN-002`
- `PATTERN-003`
- `PATTERN-004`

## Source files to change
- `schemas/runtime/*`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md` if schema/object naming needs explicit clarification
- validation wiring if schema indexes are introduced

## Generated / downstream artifacts impacted
- runtime implementation plan
- typed event payload schemas
- replay/acceptance fixtures
- generated CompanyOS IR / ExecutionSpec lowering notes

## Plan
1. Enumerate the canonical runtime objects that need schemas.
2. Define shape, required fields, scope fields, stable IDs, and linkage expectations.
3. Keep transition logic in docs/tests, not in schema overreach.
4. Document any explicitly deferred runtime object.

## Verification
- All new schemas parse and validate representative examples.
- Event-registry link targets can be mapped onto first-class runtime schemas or explicit defer notes.
- No schema duplicates a peer truth model.

## Acceptance criteria
- schemas exist for the canonical runtime objects needed by the current architecture
- runtime planning can depend on schemas instead of narrative guesswork
- schedule-first and payroll-reference semantics can both map onto the same object contracts

## Notes / decisions
Minimum expected objects include workflow_run, task_run, human_task, approval, execution_session, tool_execution, pointer, projection, and ExecutionSpec.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
