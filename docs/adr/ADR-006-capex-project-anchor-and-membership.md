# ADR-006 - CAPEX project anchor and direct membership

## Status
Accepted

## Decision
CAPEX project identity is anchored by the durable `capex_projects` runtime table. `workflow_run_id` is not a project identity; workflow runs may optionally reference a project through nullable `workflow_runs.project_id`.

Timeline events may also carry nullable `timeline_events.project_id`. Event project identity is derived from an explicit `capex_project` link when present, or from a linked project-bound workflow run.

Direct project membership is represented by `project_memberships`, with one row per `(project_id, actor_type, actor_id)`. An active row grants one role:
- `project_viewer`
- `project_contributor`
- `project_admin`

These direct memberships are the narrow runtime foundation for EPIC-140. They are separate from derived authorization projections, richer CAPEX workpage/projection APIs, production dashboard posture, and CAPEX activation. The first project child API, selector/dashboard, project-scope helper, official pointer-family slices, and rebuildable authorization projections are implemented later in `TASK-0263`, `TASK-0264`, `TASK-0371`, `TASK-0265`, and `TASK-0563` against this foundation.

Revoked memberships remain in place as governed history and grant no access. Regranting a revoked actor reactivates the same row with the newly requested role, rather than creating a parallel membership row.

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
- Membership revocations are admin-only, update the direct membership row to `revoked`, and emit `capex.project_membership.revoked`.
- Generic project-scoped artifact/task/flag/approval/pointer APIs, the max-five project selector/dashboard slice, the project-scope helper, and official pointer-family substrate are follow-on EPIC-140 work that must preserve the same direct-membership read boundary.
- Derived authorization projections exist as rebuildable read models after `TASK-0563`; authorization reads must still fail closed against live direct membership state. Pointer-promotion policy checks, data-governance gates, release/deploy work, and CAPEX runtime activation remain separately blocked.
