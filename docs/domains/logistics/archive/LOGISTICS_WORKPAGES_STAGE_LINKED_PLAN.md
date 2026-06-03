> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md

## Purpose
This plan turns the current workpage implementation into a workflow-stage operating surface.

The repo already proves three layers:
- demo compatibility aliases to workpages
- canonical `(workflow run, workpage kind) -> workpage`
- canonical `artifact version -> artifact-backed workpage -> superseding artifact version`

The next layer is:

`(workflow run, supported subject surface, workpage kind) -> stage-linked workpage action`

## Grounded current repo state
The current repo already includes:
- canonical run-backed workpage routes for schedule and EOD
- artifact-backed EOD editing
- artifact-backed Stage04 schedule draft editing
- demo-shell discovery and canonical `/runs/:workflowRunId/workpages/*` routes

The repo does not yet make workpages first-class workflow-stage actions.

The key grounded constraints are:
- `WorkspaceTaskBoard.tsx` still centers required uploads around upload/download/open-draft actions
- `RunWorkspacePage.tsx` still carries legacy schedule notice posture and should not be broadened into a general workspace rewrite in this epic
- `task_requirements.py` still reflects legacy schedule-planning mappings and does not yet distinguish relation kinds for workpage-safe requirement satisfaction
- `artifact_effects.py` already supports explicit `links[]` payloads with `relation_kind`, so the repo has a usable write-boundary seam for subject-linked artifact creation

Known baseline caveat:
- targeted workpage verification still has one pre-existing EOD submit-path failure in `tests/runtime/api/test_workpages_run_eod_contract.py::test_eod_workflow_run_workpage_uses_latest_draft_after_submit`, traced to `src/onetruth/application/services/dispatch_reporting_workbook.py`
- `TASK-0146` records that caveat but does not fix it

## TASK-0146 freeze

### 1) Workpage actions are additive projections, not a second authority model
Action metadata lives on workspace work items only:
- `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`
- `user_work[]`
- `blocking_work[]`

It does not live on:
- `graph.nodes[]`
- a separate top-level action map
- a new route family or top-level shell

Frozen additive action shape:

```json
{
  "action_id": "workpage.schedule-v0.open_latest_draft",
  "workpage_kind": "schedule-v0",
  "label": "Open schedule draft",
  "presentation": "open_route",
  "state": "available",
  "route": "/runs/wr-123/workpages/schedule-v0/artifacts/av-456",
  "create_path": null,
  "subject_context": {
    "subject_kind": "human_task",
    "subject_id": "ht-123",
    "workflow_run_id": "wr-123"
  },
  "link_policy": {
    "create_relation_kind": null,
    "submit_relation_kind": "response"
  },
  "disabled_reason": null
}
```

Frozen `presentation` values:
- `open_route`
- `create_draft_then_open`

Frozen routing posture:
- `route` stays inside the existing canonical frontend family
  - `/runs/:workflowRunId/workpages/*`
  - `/runs/:workflowRunId/workpages/*/artifacts/:artifactVersionId`
- `create_path` stays inside the existing canonical API family
- no query-param truth, no alternate shells, and no second workpage route family are introduced here

### 2) Supported-surface matrix stays intentionally small

| Workflow | Surface | Supported subject | Action target | Presentation | Notes |
|---|---|---|---|---|---|
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage04/work_item` | latest canonical schedule artifact route | `open_route` | Bounded Stage04 draft-edit lane. No create route exists. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage05/information_request` | latest canonical schedule artifact route | `open_route` | Access is for draft review/edit context only. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage05/final_review` | latest canonical schedule artifact route | `open_route` | Review access only, not publish or finalization. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | approval `scope_ref=Stage06` | latest canonical schedule artifact route | `open_route` | Approval access stays distinct from approval response. |
| `dispatch_reporting.v1` | `/runs/:workflowRunId/workspace` work items | approval `scope_ref=Stage04` | latest canonical EOD artifact route if present, else canonical EOD create route | `open_route` or `create_draft_then_open` | Approval access only, no implicit approval response. |

Not frozen in `TASK-0146`:
- graph nodes
- `/demo/logistics` story-board work items
- `/board`
- `/my-work`
- `/approvals`
- `/runs/:workflowRunId` detail tabs
- `live_dispatch.v1`
- Stage06 publish editing
- Stage07 seed/live-dispatch editing
- EOD final packet or finalization

Dispatch-reporting human-task support is intentionally not frozen in this task because the current authored/runtime posture proves the approval-backed EOD lane, not a stable task-backed EOD workpage lane.

### 3) `draft` and `response` remain semantically distinct
- `attachment`: existing upload/evidence semantics remain unchanged
- `draft`: used only for in-progress workpage draft association
- `response`: used only on the new artifact version created by workpage submit when the submit is launched from a supported subject surface

Frozen semantics:
- `draft` never satisfies required uploads
- `draft` never satisfies required reviews
- `draft` never counts as an approval response
- `draft` never advances completion or finalization truth
- `open_route` actions create no link by themselves
- weekly schedule actions freeze to `create_relation_kind=null` and `submit_relation_kind=response`
- dispatch-reporting approval actions freeze to `create_relation_kind=draft` and `submit_relation_kind=response`
- approval-review access remains distinct from approval response; opening or submitting a workpage does not call `POST /api/v1/approvals/{id}/respond`

### 4) Keep schedule and EOD asymmetric
Preserve the current asymmetry:
- schedule: run-backed landing plus bounded Stage04 artifact-backed edit lane
- EOD: run-backed landing plus artifact-backed draft creation, edit, and submit lane

Do not force them into one generic launch or write model.

## Task breakdown

### TASK-0146 - Freeze the stage-linked workpage action contract, supported-surface matrix, and subject-link semantics
Doc/contract only.

Deliverables:
- workpage-action contract freeze
- supported logistics surface matrix
- `draft` versus `response` subject-link semantics
- decision that action metadata lives on workspace work items, not graph nodes

### TASK-0147 - Backend requirement-aware artifact linkage and supported-surface policy
Backend only.

Deliverables:
- relation-kind-aware requirement counting
- supported logistics requirement matrix modernization
- optional singular `subject_link` payload support in relevant canonical workpage create/submit commands
- same-run and same-subject validation at the write boundary
- weekly Stage05 information-request requirement satisfaction limited to submitted `response` links, not `draft` or plain `attachment` links

### TASK-0148 - Backend workspace/stage-linked workpage action projection and snapshots
Projection layer.

Deliverables:
- backend-projected workpage actions on supported workspace task/approval surfaces
- generated frontend snapshots for the new workspace contracts
- explicit unavailable-state behavior when a supported surface cannot truthfully resolve a route

### TASK-0149 - Frontend workspace/task/approval workpage action integration
Frontend only.

Deliverables:
- render projected workpage actions on supported workspace cards and surfaces
- create/open latest draft handoff UX
- carry subject context into create/submit flows where needed
- refresh workspace state after create/submit so requirement truth stays synchronized

### TASK-0150 - Close EPIC-124 and synchronize docs/status/regression truth
Closeout.

Deliverables:
- status, doc, and task-memory sync
- page-map and capability updates
- regression coverage for `draft` versus `response` requirement satisfaction and stage-linked CTA rendering

## Verification expectations
At epic closeout, the repo should be able to prove:
- supported stage-native surfaces expose workpage actions from backend-projected truth
- `draft` artifacts linked to a task do not satisfy required uploads
- submitted `response` artifacts can satisfy supported requirements
- run-backed and artifact-backed workpage routes remain canonical, and demo aliases remain secondary
- docs, status, and context packs remain synchronized

## Red-team risks
1. `draft`-link leakage: `draft` artifacts start satisfying required uploads.
2. Scope bleed: the epic broadens into a full workspace modernization.
3. Approval confusion: open-workpage CTAs become implicit approval actions.
4. Schedule overreach: the epic broadens into Stage06, Stage07, or live-dispatch edits.
5. Hidden semantics drift: frontend infers launch behavior instead of following backend-projected `workpage_actions[]`.

## Recommended order
1. Freeze contract and semantics first.
2. Fix requirement/link semantics next.
3. Then project actions in backend contracts.
4. Then wire frontend CTA rendering and handoffs.
5. Close with docs and regression proof.
