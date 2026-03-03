---
id: TASK-0043
epic: EPIC-040
title: "Implement Schedule Planning Stage06 publish slice and CLI-driven scenario harness"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0042"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-090.md", "codex/context/EPIC-050.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-008"]
---

## Context
TASK-0042 completed the canonical substrate (workflow/task + approvals + artifact versions + pointers) and CLI read/query surfaces. The next slice is the first real Schedule Planning business behavior: Stage06 Supervisor Review Publish with explicit completion-driven child task spawning and CLI-driven step-run scenario execution.

## Objective
Implement the first narrow Schedule Planning runtime business slice for Stage06:
- add a Stage06-specific runtime service for conditional follow-on task spawning from completion outcomes,
- execute Stage06 flow scenarios step-by-step through the CLI boundary,
- seed runs with synthetic template-pack example artifacts,
- add scenario/runtime tests and read-contract stability tests for board/query surfaces,
- keep docs/task memory aligned with implemented behavior.

## Non-goals
- Do not build frontend/UI.
- Do not build HTTP API unless a plan doc requires it.
- Do not implement full Stage03->Stage07 flow.
- Do not build a generic workflow-engine abstraction.
- Do not implement full projection/coherence engine.
- Do not implement full Stage07 issue-loop logic.
- Do not create a second source of truth or UI-owned shadow state.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `codex/tasks/TASK-0041-workflow-task-core-and-transactional-events.md`
- `codex/tasks/TASK-0042-approvals-artifacts-pointers-and-query-surfaces.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/event_model.md`

## Source files to change
- `src/onetruth/application/services/schedule_planning_stage06.py` (new)
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/cli/__main__.py` (only if CLI boundary needs minimal extension)
- `fixtures/scenarios/schedule_planning/*.yaml` (new)
- `tests/runtime/helpers/*` (new harness helpers)
- `tests/runtime/scenarios/*.py` (new)
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py` (new)
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `README.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`

## Generated / downstream artifacts impacted
- first implementation-backed stage scenario corpus under `fixtures/scenarios/schedule_planning/`
- future board/query frontend work consuming stable CLI read contracts
- future Stage06/Stage07 runtime work extending from explicit spawned-child lineage

## Plan
1. Add narrow Stage06 service for completion outcome -> child spawn mapping.
2. Hook Stage06 spawn into transactional task completion path with lineage fields and event emission.
3. Add scenario fixtures for happy path, info-request branch, and retry-idempotency branch.
4. Build CLI-driven scenario harness utilities under `tests/runtime/helpers`.
5. Add runtime scenario tests and query-contract tests against real scenario states.
6. Update docs/task memory and run full repo verification.

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime/scenarios`
- `pytest -q tests/runtime/contracts`
- `pytest -q`

## Acceptance criteria
- Narrow Stage06 service exists with explicit outcome handling:
  - `review_requires_more_information` -> child Stage06 `information_request`
  - `review_requests_changes` -> child Stage05 `work_item`
  - `draft_is_publish_ready` -> child Stage06 `final_review`
- Child tasks are created transactionally from parent completion with lineage fields populated.
- Scenario fixtures exist under `fixtures/scenarios/schedule_planning/`.
- Runtime scenario tests execute Stage06 flow step-by-step through CLI boundary.
- Retry/idempotency behavior prevents duplicate child task creation/events.
- Query-contract tests assert stable JSON row shapes for human tasks, approvals, pointers, and workflow runs.
- `docs/planning/EVENT_EMISSION_MATRIX.md` reflects Stage06 slice behavior.
- README/planning/status docs are updated and non-stale.
- Full repo verification passes.

## Notes / decisions
- This PR is the first implementation-backed bridge between the canonical substrate, the Schedule Planning contract pack, and future human-in-the-loop board/query UX.
