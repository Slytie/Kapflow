# WORKFLOW_WORKSPACE_UI.md

Frontend design note for the single-run workflow workspace surface.

## A) Layout
- **Top:** minimal live workflow graph projected from `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`.
- **Bottom:** actionable work panel (`user_work` default, optional toggle to `blocking_work`).
- **Right:** existing `DetailDrawer` remains the deep-inspection surface.

Page composition:
- `RunWorkspacePage` hosts summary + graph + action panel.
- Graph is SVG/CSS-only (`WorkflowGraph`, `WorkflowGraphNode`, `WorkflowGraphLegend`).
- Action panel reuses existing cards (`TaskCardWide`, `ApprovalCard`, `FlagCard`) and inline attachment affordances.

## B) Interaction Rules
- Actionability is explicit and server-driven (`available_actions`, `missing_required_inputs`).
- Upload/download controls remain visible inline on cards.
- `complete` is disabled when the workspace projection returns unmet requirements.
- Stage06 AI review action is rendered only when `run_stage06_agent_review` is available.
- Polling remains first-class via existing React Query poll interval config.
- No push transport (websocket/SSE) is introduced in this slice.

## C) Visual Philosophy
- Minimalistic branching graph, not a BPMN editor.
- Serious operations aesthetic with compact metadata and clear status encoding.
- Graph status mirrors server projection; the client does not derive workflow truth.
- Blocking nodes are visually emphasized so operators can see what is gating progress.

## D) Route
- Workspace route: `/runs/:workflowRunId/workspace`
- Navigation affordances:
  - Runs page: `Open workspace`
  - Run detail page: `Open workspace`
  - Workspace page links back to run detail and official outputs
