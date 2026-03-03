# STEP_RUN_SCENARIO_HARNESS.md

This document defines the runtime scenario harness for Stage 4.

Its purpose is simple:
- let an agent execute each workflow step through a stable runtime interface,
- let task completion spawn explicit follow-on tasks when needed,
- assert only authoritative truth (events, tasks, approvals, artifacts, pointers).

Scaffold status note:
- TASK-0040 establishes the first stable CLI boundary (`init-db`, `events append`, `events list`) that runtime step-run harness work will drive and extend.
- TASK-0041 and TASK-0042 extend that boundary with workflow/task/approval/artifact/pointer lifecycle commands and query-ready list/show surfaces so step-run and future board/query UI work can proceed in parallel against stable JSON contracts.
- TASK-0043 implements the first Schedule Planning Stage06 scenario harness slice:
  - scenario fixtures in `fixtures/scenarios/schedule_planning/`
  - helper layer in `tests/runtime/helpers/scenario_harness.py`
  - CLI-driven Stage06 scenario tests in `tests/runtime/scenarios/`
  - query-contract stability tests in `tests/runtime/contracts/`
- TASK-0044 adds scenario-backed API contract/mutation tests under `tests/runtime/api/` so frontend work can validate against a stable HTTP boundary in parallel with CLI-driven scenario execution.
- TASK-0045 extends the same harness with Stage07 issue-loop fixtures and maintenance actions (`flags`, `stage07 activate-issue`, `maintenance sweep/reconcile`) plus Stage07 scenario and query-contract coverage.

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

Implemented command surface for first scenario slice:
- `onetruthctl runs create`
- `onetruthctl tasks create`
- `onetruthctl tasks claim`
- `onetruthctl tasks complete`
- `onetruthctl tasks list`
- `onetruthctl approvals request`
- `onetruthctl approvals respond`
- `onetruthctl artifacts create-version`
- `onetruthctl pointers promote`
- `onetruthctl flags create|transition|list`
- `onetruthctl stage07 activate-issue`
- `onetruthctl maintenance sweep-leases|reconcile-stage07`
- `onetruthctl events list`

Equivalent HTTP APIs are acceptable, but the scenario harness should not call hidden domain internals directly.

## 4) Scenario spec shape

Scenario-spec locations:
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
- retry parent completion -> no duplicate child tasks

Implemented in TASK-0043:
- `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`
- `tests/runtime/scenarios/test_schedule_stage06_request_more_information_steps.py`
- `tests/runtime/scenarios/test_schedule_stage06_retry_no_duplicate_child_tasks.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`

Implemented in TASK-0045:
- `tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`
- `tests/runtime/scenarios/test_schedule_stage07_missing_information_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_child_issue_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_duplicate_flag_retry.py`
- `tests/runtime/scenarios/test_schedule_stage07_lease_expiry_recovery.py`
- `tests/runtime/scenarios/test_schedule_stage07_drift_detected.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage07.py`

## 8) Code/test locations once runtime work starts

- runtime tests: `tests/runtime/scenarios/`
- scenario fixtures: `fixtures/scenarios/schedule_planning/`
- helper utilities: `tests/runtime/helpers/` if needed

The existing `tests/helpers/` folder remains the non-authoritative replay/oracle layer.
The new scenario harness should test the real runtime instead of becoming another shadow implementation.
