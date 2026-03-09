---
id: TASK-0063
epic: EPIC-025
title: "Reporting→planning feedback slice and canonical three-workflow demo story seam"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0062"]
risk: high
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Land the minimum backend/runtime/query seam needed to demo a true three-workflow logistics story over canonical runtime truth:
- confirm and keep bounded `dispatch_reporting.Stage05 -> weekly_schedule_planning.Stage03` `notify_only` feedback semantics,
- freeze a canonical first-story contract for weekly planning + live dispatch + dispatch reporting + reporting feedback,
- expose one authoritative backend story payload that the frontend can consume without client-side composition inference.

## Non-goals
- no availability-request runtime in this task
- no timecard-audit runtime in this task
- no content-derived transform semantics
- no live connector integrations
- no second composition model or second activation ontology

## Test-First Plan
1. Verify existing reporting->planning runtime tests/scenarios still pass and remain the authority for bounded `notify_only` semantics.
2. Add failing three-workflow seeded scenario coverage that exercises both handoff edges in one run lineage.
3. Add failing API contract tests for one backend-owned three-workflow story payload (graph + handoffs + linked runs + board work + official outputs + freshness/coherence).
4. Implement route/query composition only after tests fail for the missing story seam.

## Oracle
Success is demonstrated by:
- canonical story contract exists in repo-native form (`docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml`),
- existing reporting->planning `notify_only` slice remains deterministic and replay-safe,
- one seeded three-workflow scenario links reporting, weekly, and live runs through both canonical edges,
- `GET /api/v1/stories/logistics-three-workflow` returns a single backend-authored payload with family graph, handoff summaries, linked runs, board-ready work items, official-output summary, and freshness/coherence metadata.

## Source Files Changed
- `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml`
- `templates/THREE_WORKFLOW_DEMO_STORY.template.yaml`
- `templates/THREE_WORKFLOW_DEMO_STORY.example.yaml`
- `fixtures/scenarios/logistics/three_workflow_demo_story_seed.yaml`
- `tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py`
- `src/onetruth/api/routes/logistics_story.py`
- `src/onetruth/api/main.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`
- status/task-index/epic/context docs updated for freshness

## Verification Run
- `make schema-validate`
- `python3 scripts/validate_repo.py`
- `pytest -q tests/runtime/test_logistics_handoff_runtime.py`
- `pytest -q tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py`
- `pytest -q tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py`
- `pytest -q tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`

## Completion Notes (2026-03-09)
- Confirmed bounded reporting->planning `notify_only` runtime semantics remained complete; no second truth path or second runtime model was introduced.
- Added a canonical three-workflow story contract and seeded scenario that composes reporting->planning feedback with weekly->live handoff in one lineage slice.
- Added authoritative backend story query endpoint (`GET /api/v1/stories/logistics-three-workflow`) so FE can render one logistics story from server-composed canonical runtime state.
