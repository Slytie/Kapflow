---
id: TASK-0045
epic: EPIC-040
title: "Implement first Stage07 issue-scoped replan loop over canonical runtime"
status: TODO
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0044"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-090.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-008"]
---

## Context
Stage06 publish-path and board/query HTTP contracts now exist over the canonical substrate. The next runtime business slice is Stage07 issue-scoped replan behavior with explicit child-loop semantics, bounded spawning, and canonical delta/pointer evidence.

## Objective
Implement the first Stage07 issue-scoped replan loop using the existing canonical workflow/task/approval/artifact/pointer substrate and scenario harness.

## Non-goals
- Do not introduce a second workflow engine.
- Do not move canonical lifecycle semantics into frontend state.
- Do not bypass canonical approvals/pointers/events.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `codex/tasks/TASK-0043-stage06-publish-scenario-and-runtime-harness.md`
- `codex/tasks/TASK-0044-hitl-http-query-adapter-and-board-contracts.md`

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q`

## Acceptance criteria
- Stage07 issue-scoped task loop semantics are implementation-backed and scenario-tested.
- Retry/idempotency and spawn-budget behavior are explicit and test-covered.
- Canonical event/state evidence remains one-truth and transactionally emitted.
- README/planning/task docs are updated to reflect implemented behavior.
