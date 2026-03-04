---
id: TASK-0057
epic: EPIC-040
title: "Workflow workspace projection, graph actionability, demo runner, and export bundle"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops", "security"]
depends_on: ["TASK-0045", "TASK-0048", "TASK-0051", "TASK-0052", "TASK-0054"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Objective
Implement the backend slice for a single-run workflow workspace demo:
- derived workflow workspace projection for one workflow run,
- minimal branching graph projection for `schedule_planning.v1`,
- server-computed actionability for tasks/approvals/exceptions,
- demo runner and export bundle so a human can inspect and act after the run.

The graph/workspace layer is read-oriented and derived from canonical runtime records.

## Non-goals
- no generalized workflow/graph engine,
- no UI-owned workflow semantics,
- no websocket/SSE stream in this task,
- no second official status path outside canonical events/artifacts/pointers/task/approval/flag rows,
- no replacement of existing canonical mutation handlers/endpoints.

## Source Files To Read First
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`
- `docs/planning/STAGE07_RUNTIME_MODEL.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `src/onetruth/api/main.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/api/routes/approvals.py`
- `src/onetruth/api/routes/flags.py`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/timeline.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/schedule_planning_stage06.py`
- `src/onetruth/application/services/schedule_planning_stage07.py`
- `src/onetruth/application/services/example_document_corpus.py`
- `src/onetruth/infrastructure/repositories/*`
- `fixtures/example_document_corpus/manifest.yaml`
- `fixtures/example_document_corpus/seed_sets.json`
- `fixtures/scenarios/schedule_planning/*.yaml`
- `fixtures/frontend_contracts/*`
- `tests/runtime/api/*`
- `tests/runtime/scenarios/*stage06*`
- `tests/runtime/scenarios/*stage07*`

## Source Files To Change
- `src/onetruth/application/projections/workspace_graphs/base.py`
- `src/onetruth/application/projections/workspace_graphs/registry.py`
- `src/onetruth/application/projections/workspace_graphs/schedule_planning.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/api/main.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `scripts/run_schedule_workspace_demo.py`
- `scripts/export_run_workspace_bundle.py`
- `tests/runtime/api/*workspace*`
- `tests/runtime/contracts/*workspace*`
- `tests/runtime/scenarios/*workspace*`
- `tests/unit/*task_actionability*`
- `docs/planning/WORKFLOW_WORKSPACE_DEMO_AND_GRAPH.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `README.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0057-workflow-workspace-projection-and-demo-runner.md`

## Verification Commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `make runtime-api`
- `pytest -q`
- `PYTHONPATH=src pytest -q tests/runtime/api tests/runtime/contracts tests/runtime/scenarios tests/unit`
- `PYTHONPATH=src python3 scripts/run_schedule_workspace_demo.py --db-url sqlite:///./.tmp/workspace-demo.db --scenario stage06_publish_ready`
- `PYTHONPATH=src python3 scripts/export_run_workspace_bundle.py --db-url sqlite:///./.tmp/workspace-demo.db --workflow-run-id <run_id> --output ./.tmp/workspace-bundle.zip`

## Acceptance Criteria
- schedule-planning graph projector exists and is explicitly derived from canonical runtime state.
- `GET /api/v1/workflow-runs/{workflow_run_id}/workspace` exists and is read-only.
- workspace items expose server-computed `available_actions` and blocking requirements.
- information-request actionability requires at least one linked artifact before completion is available.
- Stage06 review actionability exposes `run_stage06_agent_review` only when policy/role conditions allow.
- demo runner creates realistic seeded run(s) and emits `workflow_run_id` + recommended workspace URL.
- export bundle zip is created and includes required workspace/run/timeline/graph/actionability artifacts.
- tests cover graph projection, actionability transitions, endpoint envelope and scope denial, demo run output, and export zip contents.
- docs and README are updated with concrete commands and no stale future-tense references.

## Explicit Authority Notes
- Graph/workspace are derived projections and never authoritative truth.
- Bottom action panel in workspace is a canonical-mutation surface only: claim/complete/respond/upload/transition continue to delegate to existing canonical handlers and APIs.

## Completion Notes (2026-03-04)
- Implemented:
  - derived schedule-planning workspace graph projector (`src/onetruth/application/projections/workspace_graphs/*`)
  - server-computed actionability service (`src/onetruth/application/services/task_actionability.py`)
  - read-only workspace endpoint (`GET /api/v1/workflow-runs/{workflow_run_id}/workspace`)
  - workspace demo runner (`scripts/run_schedule_workspace_demo.py`)
  - workspace export bundle generator (`scripts/export_run_workspace_bundle.py`)
  - runtime coverage for graph/actionability/endpoint/demo/export behavior
- Final verification command results:
  - `make schema-validate` passed
  - `make contract` passed
  - `make replay` passed
  - `make acceptance` passed
  - `make runtime` passed
  - `make runtime-api` passed
  - `pytest -q` passed
  - targeted workspace suites passed
- Demo + export execution:
  - demo scenario `stage06_publish_ready` created `workflow_run_id=wr-497ee868ca8a177576f55d3b`
  - bundle exported to `./.tmp/workspace-bundle-step11.zip`
