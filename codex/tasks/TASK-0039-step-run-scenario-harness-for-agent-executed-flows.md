---
id: TASK-0039
epic: EPIC-090
title: Design the step-run scenario harness for agent-executed flows and conditional task spawning
status: DONE
owners:
- qa
- platform
reviewers:
- ops
- security
depends_on:
- TASK-0028
- TASK-0029
- TASK-0035
risk: high
context_packs:
- codex/context/EPIC-090.md
patterns:
- PATTERN-002
- PATTERN-008
---

## Context
The repo now has a replay-first oracle layer and synthetic completed example artifacts in the workflow template packs. What is still missing is the runtime scenario harness that will let a coding agent execute each step through the real command boundary and assert authoritative events, approvals, pointers, and child-task lineage.

## Objective
Define the runtime step-run scenario harness for Schedule Planning so:
- an agent can execute each step through a stable interface,
- task completion may spawn explicit follow-on tasks,
- tests assert authoritative truth and idempotency instead of hidden internals.

## Non-goals
- Do not build browser/UI automation as the primary Stage 4 harness.
- Do not invent a second sample-data universe when the repo already contains synthetic completed example artifacts.
- Do not make the scenario harness depend on hidden domain methods that bypass the command/API surface.

## Source files to read first
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/human_task_semantics.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `fixtures/workflows/schedule_planning/README.md`

## Source files to change
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/TEST_MATRIX.md`
- `tests/runtime/` once runtime code exists
- `fixtures/scenarios/schedule_planning/` once the scenario specs are authored

## Generated / downstream artifacts impacted
- runtime scenario fixtures
- CI acceptance/runtime gates
- future generated runbooks that document executable step flows

## Plan
1. Freeze the stable CLI/API surface that the runtime scenarios should drive.
2. Define the scenario-spec format and storage locations.
3. Specify how synthetic completed example artifacts seed scenario inputs.
4. Name the first required Schedule Planning scenarios, including conditional child-task spawning and retry/idempotency checks.

## Verification
- the harness design names stable runtime entrypoints
- the harness design names scenario fixture locations
- the harness design explicitly asserts child-task lineage and retry-safe spawning
- the harness uses the existing example artifacts in `fixtures/workflows/*/template_pack/`

## Acceptance criteria
- a fresh coding agent can tell how runtime step tests should be structured
- task completion spawning new tasks is a first-class scenario requirement
- example artifacts already present in the repo are the planned seed inputs
- the design does not create a second truth path or a shadow test-only workflow model

## Completion notes
- Step-run scenario harness guidance is now implementation-backed in [STEP_RUN_SCENARIO_HARNESS.md](/Users/tylerclark/git/pythonProject/companyos/docs/planning/STEP_RUN_SCENARIO_HARNESS.md).
- Scenario fixtures now exist under `fixtures/scenarios/schedule_planning/`.
- CLI-driven runtime scenario harness helper exists at `tests/runtime/helpers/scenario_harness.py`.
- Stage06 scenario tests and query-contract tests were added in TASK-0043 under `tests/runtime/scenarios/` and `tests/runtime/contracts/`.
