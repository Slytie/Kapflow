# CAPEX Project Authorization CED

## Status
Accepted Wave 1 design and prototype boundary; projection runtime state is implemented as a rebuildable read model. CAPEX runtime activation remains disabled.

## Scope
This CED closes `TASK-0385`, anchors the `TASK-0386` `AuthorizedProjectsQuery` prototype, and is reconciled by `TASK-0563` physical authorization projection runtime state. It records project authorization design intent and runtime read-model posture; production activation remains later gated work.

## Decisions

`capex_projects.project_id` remains the durable CAPEX project root. In plain terms, workflow_run_id is an execution identity and may only reference a project through `workflow_runs.project_id`; it is never a project identity.

`project_memberships` remains the direct grant table. It records one active direct role per `(project_id, actor_type, actor_id)` using the existing `project_viewer`, `project_contributor`, and `project_admin` role order. Direct membership is source runtime state, not a generated user-facing projection.

`capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` are derived read-model/projection concepts:
- `capex_project_authorization` records one projected authorization row per active direct membership today and may later combine direct membership with policy, waiver, feature, and source-governance inputs.
- `capex_project_feature` describes project capability posture and activation gates; `capex.runtime_activation` is seeded as disabled.
- `capex_user_project_view` is a deterministic user-facing read model over authorized active projects.

Those future surfaces are not authoritative project truth. They must be rebuildable from canonical runtime state and policy inputs, and they must not bypass direct membership, tenant/domain isolation, audited approvals, immutable artifacts, or promotion pointers.

`AuthorizedProjectsQuery` is the Wave 1 backend-only query surface. It accepts tenant/domain scope plus actor identity and returns deterministic authorized active project IDs and caller role metadata from projection-backed rows derived from existing direct memberships. It is not a frontend-only filter, does not expose a global project list, and returns an empty result for non-members.

## Gates
This CED records the W1 project authorization interpretation for:
- `ARCH-W1-GATE-004`: `capex_project` is the durable root and `workflow_run` is not project identity.
- `ARCH-W1-GATE-005`: `project_membership` and future `capex_project_authorization` are separate.
- `ARCH-W1-GATE-006`: project-scoped runtime rows use direct `project_id` where the current foundation already added it.

## Rollback And Recovery
Rollback posture is to leave runtime state inert or keep the CAPEX capability disabled. Do not destructively delete governed `capex_projects`, `project_memberships`, workflow runs, timeline events, artifacts, approvals, flags, tasks, or pointers as a rollback mechanism.

## Explicit Non-Activation
This CED and the `TASK-0563` reconciliation do not add routes, frontend behavior, workflow packs, raw corpus handling, production-like dashboards, or CAPEX runtime activation. In short: it does not add routes or activate CAPEX product behavior.
