# STEP_RUN_SCENARIO_HARNESS.md

This document defines the planned runtime scenario harness for Stage 4.

Its purpose is simple:
- let an agent execute each workflow step through a stable runtime interface,
- let task completion spawn explicit follow-on tasks when needed,
- assert only authoritative truth (events, tasks, approvals, artifacts, pointers).

## 1) Why this harness exists

Golden traces and replay tests are already the first behavioral corpus.
They prove the semantics.

What is still needed for runtime implementation is a second layer:
- scenario tests that drive the real runtime one step at a time,
- while preserving the same one-truth event / task / approval / pointer substrate.

This is especially important now that Stage 4 explicitly allows **conditional follow-on task spawning** for dynamic loops such as:
- request more information from another role,
- send work back for changes,
- require final review after a draft is otherwise complete,
- break an exception into child issue work.

## 2) Scope

### In scope
- Schedule Planning first
- agent-owned execution of every in-scope step
- explicit child-task creation and lineage assertions
- artifact seeding from synthetic example files in `fixtures/workflows/*/template_pack/`
- idempotency checks for repeated parent completion commands

### Out of scope
- browser/UI automation as the primary Stage 4 test surface
- hidden internal method-call tests that bypass the command boundary
- a second sample-data universe separate from the workflow fixture packs

## 3) Stable runtime interface

The scenario harness should drive the runtime through a stable CLI or API surface.

Preferred command surface:
- `onetruthctl workflow-run create`
- `onetruthctl artifact import`
- `onetruthctl task list`
- `onetruthctl task claim`
- `onetruthctl task complete`
- `onetruthctl approval request`
- `onetruthctl approval respond`
- `onetruthctl pointer promote`
- `onetruthctl timeline list`
- `onetruthctl task-lineage show`

Equivalent HTTP APIs are acceptable, but the scenario harness should not call hidden domain internals directly.

## 4) Scenario spec shape

Planned scenario-spec locations:
- `fixtures/scenarios/schedule_planning/*.yaml`

Recommended fields:
- `scenario_id`
- `workflow_id`
- `scope`
- `partition_key`
- `seed_artifacts`
- `steps`
- `expected_events`
- `expected_task_states`
- `expected_spawned_children`
- `expected_pointer_targets`

A step should declare:
- command name
- input payload
- acting principal
- idempotency key
- expected immediate result

## 5) Artifact seeding rule

Use the synthetic completed examples already in the repo:
- `fixtures/workflows/schedule_planning/template_pack/*_Example_COMPLETED.*`
- `fixtures/workflows/payroll/template_pack/*_Example_COMPLETED.*`

The runtime scenario harness should:
1. copy those files into temp storage,
2. register them as imported artifact versions with synthetic IDs,
3. bind them to the workflow run under test.

Do not create a second handwritten sample-data tree when the fixture packs already contain canonical example inputs.

## 6) Assertions

Scenario tests should assert only authoritative truth:

### Events
- parent `task.completed`
- child `task.run.created`
- child `task.created`
- `approval.requested` / `approval.responded` when gates apply
- `artifact.version.created`
- `artifact.pointer.promoted`
- `artifact.pointer.drift_detected` when relevant

### State
- parent task ends in the expected state
- child tasks exist with the correct `stage_id`, `task_kind`, and lineage fields
- approvals bind to the exact reviewed evidence
- pointers target the expected official artifact versions

### Idempotency
Retrying the same parent completion command must not create duplicate child tasks.

## 7) Minimum first scenarios

### Schedule Planning
- Stage06 publish happy path with agent-owned execution
- Stage06 review requires more information -> child information-request task
- Stage06 review complete -> child final-review task before publish
- Stage07 issue triage -> child re-review / information-request task
- retry parent completion -> no duplicate child tasks

## 8) Code/test locations once runtime work starts

- runtime tests: `tests/runtime/scenarios/`
- scenario fixtures: `fixtures/scenarios/schedule_planning/`
- helper utilities: `tests/runtime/helpers/` if needed

The existing `tests/helpers/` folder remains the non-authoritative replay/oracle layer.
The new scenario harness should test the real runtime instead of becoming another shadow implementation.
