# FRONTEND_PAGE_MAP.md

## Page inventory

| Page | Purpose | Primary user action | Primary data source | Cards/Rows | Detail model |
|---|---|---|---|---|---|
| `/board` | Triage overview of task/approval/exception lanes | Claim/complete/respond from lane cards | `GET /api/v1/board/schedule-planning` + `GET /api/v1/flags` via `boardRepository` | Board cards (`TaskCardWide`, `ApprovalCard`, `FlagCard`) | Drawer |
| `/my-work` | Dense assigned queue for operator execution | Inline claim/complete and attachment actions | `GET /api/v1/human-tasks` via `humanTasksRepository` | Rows (`QueueRow`) | Drawer |
| `/approvals` | Approval queue with review workspace | Approve/reject/request changes | `GET /api/v1/approvals` + `POST /api/v1/approvals/{id}/respond` + run detail artifacts | Cards + split review pane | Split-pane + drawer |
| `/exceptions` | Exception/flag queue | Inspect severity and related run context | `GET /api/v1/flags` via `flagsRepository` | Cards (`FlagCard`) | Drawer |
| `/runs` | Workflow run list | Open run detail | `GET /api/v1/workflow-runs` via `workflowRunsRepository` | Rows (`QueueRow`) | Drawer + detail page |
| `/runs/:workflowRunId` | Full run inspection across timeline/tasks/approvals/artifacts/exceptions | Tabbed inspection | `GET /api/v1/workflow-runs/{id}` + `GET /api/v1/timeline-events` | Rows and tab lists | Page tabs + drawer hook |
| `/official-outputs` | Pointer/current official output visibility | Inspect pointer promotion metadata | `GET /api/v1/pointers` via `pointersRepository` | Cards (`PointerCard`) | Drawer |
| `/timeline` | Dense event stream explorer | Filter and inspect event details | `GET /api/v1/timeline-events` via `timelineRepository` | Rows (`TimelineRow`) | Drawer |
