# CAPEX Project Access Model

## Status
Accepted foundation, inactive CAPEX runtime.

## Scope
This document records the narrow EPIC-140 foundation implemented by `TASK-0261` and `TASK-0262`.

It does not activate CAPEX production-like runtime behavior, raw corpus use, project dashboards, authorization projections, official project pointer families, or richer project-scoped child APIs.

## Project Anchor
`capex_projects.project_id` is the durable project identity.

`workflow_run_id` is an execution instance identity. A workflow run may belong to a project through nullable `workflow_runs.project_id`, but it is never the project root.

Timeline events may carry nullable `timeline_events.project_id` so broad timeline reads can enforce project visibility without reconstructing every event link at read time.

## Direct Membership Roles
`project_memberships` records one active direct role per `(project_id, actor_type, actor_id)`.

Roles are ordered:
- `project_viewer`: read project and project-bound rows
- `project_contributor`: viewer plus create project-bound workflow runs
- `project_admin`: contributor plus direct membership management

Non-members receive not-found style denial for project reads to avoid project existence leaks. Members who lack the required write role receive a forbidden denial.

## Current API Surface
The current project API surface is intentionally minimal:
- `GET /api/v1/capex/projects`
- `POST /api/v1/capex/projects`
- `GET /api/v1/capex/projects/{project_id}`
- `GET /api/v1/capex/projects/{project_id}/memberships`
- `POST /api/v1/capex/projects/{project_id}/memberships`
- `POST /api/v1/capex/projects/{project_id}/workflow-runs`

Project creation creates the project and grants the creator `project_admin`. Membership grants are admin-only.

## Shared Read Paths
Same-tenant non-members must not see project-bound rows through broad list/detail helpers. The current enforced surfaces include:
- workflow run list/detail
- HITL human task, approval, flag, pointer, and artifact list helpers
- timeline list helpers
- existing `scoped_workflow_run` facades

No-project rows remain readable by the existing tenant/domain boundary.

## Future Work
Later EPIC-140 tasks own:
- project-scoped artifact/task/flag/approval/pointer APIs
- authorization projections and policy dependency expansion
- max-five project selector/dashboard UX
- project-scoped official pointer families
- CAPEX runtime activation and production gates
