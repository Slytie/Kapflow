# ADR-006 - CAPEX project anchor and direct membership

## Status
Accepted

## Decision
CAPEX project identity is anchored by the durable `capex_projects` runtime table. `workflow_run_id` is not a project identity; workflow runs may optionally reference a project through nullable `workflow_runs.project_id`.

Timeline events may also carry nullable `timeline_events.project_id`. Event project identity is derived from an explicit `capex_project` link when present, or from a linked project-bound workflow run.

Direct project membership is represented by `project_memberships`, with one active role per `(project_id, actor_type, actor_id)`:
- `project_viewer`
- `project_contributor`
- `project_admin`

These direct memberships are the narrow runtime foundation for EPIC-140. They are separate from authorization projections, official pointer families, richer CAPEX workpage/projection APIs, production dashboard posture, and CAPEX activation. The first project child API and selector/dashboard slice is implemented later in `TASK-0263` and `TASK-0264` against this foundation.

## Why
CAPEX work needs a durable root that can contain multiple workflow runs and remain stable across project lifecycle events. Using `workflow_run_id` as project identity would collapse project scope into one execution instance and make project-level membership, audit, and future dashboard behavior ambiguous.

Direct membership gives the runtime a minimal auth-before-read boundary now:
- non-members receive not-found style denial for project reads
- viewers can read project-bound rows
- contributors can create project-bound workflow runs
- admins can manage direct memberships

## Consequences
- Existing no-project logistics/runtime rows remain valid and readable by tenant/domain scope exactly as before.
- Project-bound workflow runs and timeline rows must be hidden from same-tenant actors who do not have direct project membership.
- Project creation emits `capex.project.created` and grants the creator `project_admin` through an audited `capex.project_membership.granted` event.
- Membership grants are admin-only and emit `capex.project_membership.granted`.
- Generic project-scoped artifact/task/flag/approval/pointer APIs and the max-five project selector/dashboard slice are follow-on EPIC-140 work that must preserve the same direct-membership read boundary.
- Authorization projections, official project pointer families, data-governance gates, release/deploy work, and CAPEX runtime activation remain separately blocked.
