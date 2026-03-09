# FRONTEND_PAGE_MAP.md

## Page inventory

| Page | Purpose | Primary user action | Primary data source | Cards/Rows | Detail model |
|---|---|---|---|---|---|
| `/demo/logistics` | Primary three-workflow operator demo shell | Open task pane from story board item, then claim/complete in drawer | `GET /api/v1/stories/logistics-three-workflow` + task detail/mutation routes via repositories | Story board items + workflow graph + linked run list | Drawer-first task actions |
| `/board` | Legacy schedule-only triage/regression view | Open task pane for task transitions; run approval/flag actions in-lane | `GET /api/v1/board/schedule-planning` + `GET /api/v1/flags` via `boardRepository` | Board cards (`TaskCardWide`, `ApprovalCard`, `FlagCard`) | Drawer |
| `/my-work` | Secondary assigned queue for operator execution | Open task pane for claim/complete; keep attachment actions inline | `GET /api/v1/human-tasks` via `humanTasksRepository` | Rows (`QueueRow`) | Drawer |
| `/approvals` | Approval queue with review workspace | Approve/reject/request changes | `GET /api/v1/approvals` + `POST /api/v1/approvals/{id}/respond` + run detail artifacts | Cards + split review pane | Split-pane + drawer |
| `/exceptions` | Exception/flag queue | Inspect severity and related run context | `GET /api/v1/flags` via `flagsRepository` | Cards (`FlagCard`) | Drawer |
| `/runs` | Supporting run list for drill-down | Open run detail | `GET /api/v1/workflow-runs` via `workflowRunsRepository` | Rows (`QueueRow`) | Drawer + detail page |
| `/runs/:workflowRunId/workspace` | Single-run operator workspace with synchronized graph + actions | Execute inline work while monitoring run progression | `GET /api/v1/workflow-runs/{id}/workspace` + existing task/approval/artifact mutation routes via repositories | Graph + cards (`TaskCardWide`, `ApprovalCard`, `FlagCard`) | Drawer |
| `/runs/:workflowRunId` | Full run inspection across timeline/tasks/approvals/artifacts/exceptions | Tabbed inspection | `GET /api/v1/workflow-runs/{id}` + `GET /api/v1/timeline-events` | Rows and tab lists | Page tabs + drawer hook |
| `/official-outputs` | Pointer/current official output visibility | Inspect pointer promotion metadata | `GET /api/v1/pointers` via `pointersRepository` | Cards (`PointerCard`) | Drawer |
| `/timeline` | Legacy schedule-oriented event stream explorer | Filter and inspect event details | `GET /api/v1/timeline-events` via `timelineRepository` | Rows (`TimelineRow`) | Drawer |
