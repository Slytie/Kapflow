---
id: TASK-0058
epic: EPIC-080
title: "Workflow workspace page, live graph, and synchronized actionable work panel"
status: DONE
owners: ["frontend"]
reviewers: ["platform", "qa"]
depends_on: ["TASK-0048", "TASK-0057"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007"]
---

## Objective
Implement the frontend half of the single-run workflow workspace demo:
- top section shows a minimal live graph projection from server data,
- bottom section shows current-user actionable work and optional blocking work,
- inline card actions remain canonical mutation paths and visibly unblock workflow progress.

The workspace page must reuse the existing app shell, repository boundaries, drawer model, inline attachment actions, and React Query polling model.

## Non-goals
- no heavyweight graph library,
- no client-owned workflow semantics,
- no drag-and-drop state transitions,
- no websocket/SSE transport in this task,
- no mutation logic forked away from existing repositories.

## Source Files Read
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/pages/BoardPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/MyWorkPage.tsx`
- `frontend/src/components/TaskCardWide.tsx`
- `frontend/src/components/ApprovalCard.tsx`
- `frontend/src/components/FlagCard.tsx`
- `frontend/src/components/QueueRow.tsx`
- `frontend/src/components/DetailDrawer.tsx`
- `frontend/src/lib/repositories/*`
- `frontend/src/lib/types/contracts.ts`
- `frontend/src/lib/types/ui.ts`

## Source Files Changed
- `frontend/src/app/App.tsx`
- `frontend/src/app/app.css`
- `frontend/src/pages/RunWorkspacePage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/runWorkspacePage.test.tsx`
- `frontend/src/pages/runsPage.test.tsx`
- `frontend/src/components/ActionCluster.tsx`
- `frontend/src/components/TaskCardWide.tsx`
- `frontend/src/components/ApprovalCard.tsx`
- `frontend/src/components/WorkflowGraph.tsx`
- `frontend/src/components/WorkflowGraphNode.tsx`
- `frontend/src/components/WorkflowGraphLegend.tsx`
- `frontend/src/components/WorkspaceSummaryBar.tsx`
- `frontend/src/components/WorkspaceActionPanel.tsx`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workflowRunsRepository.ts`
- `frontend/src/lib/repositories/humanTasksRepository.ts`
- `frontend/src/lib/repositories/artifactAttachments.ts`
- `frontend/src/lib/types/contracts.ts`
- `frontend/src/test/api/contractState.ts`
- `frontend/src/test/api/handlers.ts`
- `docs/planning/WORKFLOW_WORKSPACE_UI.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `README.md`

## Verification Commands
- `cd frontend && npm install`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test:run`
- `cd frontend && npm run build`

## Acceptance Criteria
- `/runs/:workflowRunId/workspace` route exists and loads.
- Graph projection is rendered from `/api/v1/workflow-runs/{workflow_run_id}/workspace`.
- Action panel defaults to `user_work` and can toggle to `blocking_work`.
- Existing inline card actions still run through repositories.
- `complete` is disabled when `missing_required_inputs` is non-empty.
- Upload action can unblock a previously non-completable task projection.
- Stage06 AI action appears only when `run_stage06_agent_review` is present.
- Runs and run-detail pages expose direct "Open workspace" navigation.
- Frontend tests cover graph rendering, action panel behavior, route loading, and state handling.
- Frontend typecheck/tests/build remain green.
