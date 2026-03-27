# LOGISTICS_WORKPAGES_STAGE_LINKED_BRIEF.md

## Executive summary
The repo already proves three bounded workpage layers for the logistics family:
- demo compatibility aliases
- canonical run-backed workpages under `/runs/:workflowRunId/workpages/*`
- canonical artifact-backed workpage editing over immutable artifact versions

The next missing layer is to make those existing workpages reachable from the workflow-stage surfaces operators actually use, without inventing a second truth path:

`(workflow run, supported subject surface, workpage kind) -> stage-linked workpage action`

`TASK-0146` freezes that layer as a doc/contract boundary only.

## Problem statement
Today the repo can open workpages from:
- `/demo/logistics`
- canonical `/runs/:workflowRunId/workpages/*`
- canonical artifact-backed workpage routes

But the repo still does not treat workpages as first-class actions on the stage-native surfaces that matter most for operators:
- workspace human-task cards
- workspace approval cards

At the same time, requirement satisfaction and artifact linkage are still legacy in important places:
- `task_requirements.py` still reflects older schedule-planning assumptions
- requirement satisfaction is not yet safely relation-kind-aware for workpage `draft` versus submitted `response` semantics
- workpage create/submit flows are not yet the canonical mechanism for satisfying stage-linked upload/review expectations

## Goal
Make supported logistics workpages available as stage-linked actions while preserving the one-truth model:
- workpages remain derived surfaces
- artifacts remain canonical truth
- create/submit flows can optionally link artifacts back to the triggering task/approval surface
- `draft` links must not satisfy required uploads
- `response` links may satisfy supported requirements when later backend policy work says they should

## TASK-0146 contract freeze
- Put additive `workpage_actions[]` only on workspace work-item rows returned by `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`.
- Keep workpage launch semantics off graph nodes, off separate top-level maps, and off any new route family.
- Freeze exactly two action presentations:
  - `open_route`
  - `create_draft_then_open`
- Keep all action routes inside the existing canonical frontend route family:
  - `/runs/:workflowRunId/workpages/*`
  - `/runs/:workflowRunId/workpages/*/artifacts/:artifactVersionId`
- Keep all create paths inside existing canonical API families; do not invent a second shell or second workpage route system.

## First supported surfaces
The first frozen support matrix is intentionally small:
- `weekly_schedule_planning.v1` workspace work items for Stage04 and selected Stage05/Stage06 review surfaces open the latest canonical schedule draft artifact route
- `dispatch_reporting.v1` workspace approval work items for `scope_ref=Stage04` open the latest canonical EOD artifact route, or create a draft first and then open it

This task does not freeze support for:
- graph nodes
- `/demo/logistics` story-board work items
- `/board`
- `/my-work`
- `/approvals`
- `/runs/:workflowRunId` detail tabs
- `live_dispatch.v1`
- Stage06 publish editing
- Stage07 seed/live-dispatch editing
- EOD final packet or finalization flows

## Red-team constraints
- Do not make approval-review access equivalent to approval completion.
- Do not let `draft` links satisfy required uploads.
- Do not silently redefine existing run-backed or artifact-backed routes.
- Do not broaden into schedule write-path widening or EOD finalization.
- Do not turn this epic into a general workspace rewrite.

## Success criteria
This epic succeeds when:
1. Supported workspace task/approval surfaces expose truthful workpage actions.
2. Those actions resolve to the existing canonical run-backed or artifact-backed workpage routes.
3. Workpage create/submit flows can attach the correct subject links when launched from a supported surface.
4. `draft` links do not satisfy requirements.
5. Submitted `response` artifacts can satisfy supported requirements safely and truthfully.
6. Repo memory and docs stay synchronized so fresh Codex runs do not drift.
