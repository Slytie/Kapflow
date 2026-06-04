# CAPEX Project Access Model

## Status
Accepted foundation, inactive CAPEX runtime.

## Scope
This document records the narrow EPIC-140 foundation implemented by `TASK-0261` through `TASK-0265` plus `TASK-0371`.

It does not activate CAPEX production-like runtime behavior, raw corpus use, authorization projections, richer CAPEX workpages, or production dashboards.

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

## Project API Surface
The current project API surface includes the durable anchor, direct membership, and project-bound run creation:
- `GET /api/v1/capex/projects`
- `POST /api/v1/capex/projects`
- `GET /api/v1/capex/projects/{project_id}`
- `GET /api/v1/capex/projects/{project_id}/memberships`
- `POST /api/v1/capex/projects/{project_id}/memberships`
- `POST /api/v1/capex/projects/{project_id}/workflow-runs`

Project creation creates the project and grants the creator `project_admin`. Membership grants are admin-only.

Project list/detail payloads expose `caller_role` from the caller's active direct membership.

## Project Child API Surface
Project-scoped child routes live below `/api/v1/capex/projects/{project_id}`. They preserve the existing global row and action payload shapes, add project-scoped command names where command responses are returned, and stamp returned child rows with `project_id`.

Workflow run routes:
- `GET /workflow-runs`
- `GET /workflow-runs/{workflow_run_id}`
- `GET /workflow-runs/{workflow_run_id}/workspace`
- `GET /workflow-runs/{workflow_run_id}/timeline`
- `GET /workflow-runs/{workflow_run_id}/artifacts`
- `POST /workflow-runs/{workflow_run_id}/artifacts/upload`

Human task routes:
- `GET /human-tasks`
- `GET /human-tasks/{human_task_id}`
- `GET /human-tasks/{human_task_id}/subgraph`
- `POST /human-tasks/{human_task_id}/claim`
- `POST /human-tasks/{human_task_id}/complete`
- `POST /human-tasks/{human_task_id}/confirm-review`
- `GET /human-tasks/{human_task_id}/artifacts`
- `POST /human-tasks/{human_task_id}/artifacts/upload`

Approval routes:
- `GET /approvals`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/respond`
- `GET /approvals/{approval_id}/artifacts`
- `POST /approvals/{approval_id}/artifacts/upload`

Flag routes:
- `GET /flags`
- `GET /flags/{flag_id}`
- `POST /flags/{flag_id}/transition`
- `GET /flags/{flag_id}/artifacts`
- `POST /flags/{flag_id}/artifacts/upload`

Artifact, pointer, and timeline routes:
- `GET /artifacts`
- `GET /artifacts/{artifact_version_id}`
- `GET /artifacts/{artifact_version_id}/download`
- `GET /artifacts/{artifact_version_id}/download.bin`
- `GET /pointers`
- `GET /pointers/{pointer_id}`
- `GET /timeline-events`

Every project child read first requires project viewer membership, then verifies that the child row belongs to the path project before delegating to the existing handler. Missing projects, non-members, missing children, and project mismatches use not-found style denial to avoid existence leaks.

## Project Official Pointer Families
Project-scoped official pointer families live below `/api/v1/capex/projects/{project_id}`:
- `GET /official-pointers`
- `GET /official-pointers/{pointer_family}`
- `POST /official-pointers/{pointer_family}/promote`

These routes are project policy around the canonical `artifact_pointers` substrate. They do not add a new pointer table, change pointer ID format, or mutate immutable artifacts.

Derived pointer fields:
- `scope_kind=capex_project`
- `scope_ref={project_id}`
- `pointer_key=official:{pointer_family}`
- `stream_key=capex-project:{project_id}:pointer-family:{pointer_family}`
- existing pointer `generation` tracks compare-and-set promotion order

Reads require project viewer membership. Promotion requires contributor/admin membership, explicit `workflow_run_id`, `artifact_version_id`, `artifact_kind`, and `idempotency_key`, and validates that workflow-run, artifact, optional approval evidence, and optional task evidence belong to the path project before delegating to canonical pointer promotion.

Approval responses, approved approvals, and latest artifact versions do not move project official pointers by themselves. Officialness changes only through explicit pointer promotion.

Route responses return the canonical pointer row plus derived `project_id` and `pointer_family`, and include a snapshot with `project_id`, `pointer_family`, `pointer_id`, `artifact_version_id`, `artifact_kind`, `generation`, and `updated_at`.

## Dashboard and Selector
`GET /api/v1/capex/projects/{project_id}/dashboard` returns a derived, non-authoritative dashboard projection:
- `project` and `caller_role`
- counts for workflow runs, open human tasks, pending approvals, active flags, artifact versions, pointers, and timeline events
- small paged excerpts for recent runs and active work

The frontend selector lives at `/capex/projects` and `/capex/projects/:projectId`. It shows up to five active assigned projects by default, displays caller role visibly, and links selected project rows to existing run/work/task queues. It does not redirect the app root, alter logistics routes, or imply CAPEX runtime activation.

## Shared Read Paths
Same-tenant non-members must not see project-bound rows through broad list/detail helpers. The current enforced surfaces include:
- workflow run list/detail
- HITL human task, approval, flag, pointer, and artifact list helpers
- timeline list helpers
- existing `scoped_workflow_run` facades

No-project rows remain readable by the existing tenant/domain boundary.

## Index Coverage
This tranche adds no new database migration. Project child route filtering uses:
- `workflow_runs.project_id` for project-bound run selection
- `timeline_events.project_id`, falling back through linked `workflow_runs.project_id`, for project timeline reads
- existing child `workflow_run_id` index coverage for human tasks, approvals, flags, artifact versions, artifact links, and artifact pointers

`tests/integration/test_capex_project_schema_parity.py` records the schema/index parity evidence.

## Future Work
Later EPIC-140 tasks own:
- authorization projections and policy dependency expansion
- richer CAPEX workpages/projections and production dashboard posture
- CAPEX runtime activation, raw-corpus governance, and production gates
