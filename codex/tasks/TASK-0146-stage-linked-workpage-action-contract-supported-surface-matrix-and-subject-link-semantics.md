---
id: TASK-0146
epic: EPIC-124
title: "Freeze the stage-linked workpage action contract, supported-surface matrix, and subject-link semantics"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0145"]
risk: medium
context_packs: ["codex/context/EPIC-124.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The repo already has canonical run-backed and artifact-backed workpage routes, but the workflow-stage surfaces still do not expose backend-projected workpage actions. Before any more implementation, the repo needs one frozen contract for how task/approval/workspace surfaces refer to workpages and how draft-vs-response semantics should work.

The post-EPIC-123 baseline is structurally present, but a known pre-existing regression remains in targeted workpage verification: `tests/runtime/api/test_workpages_run_eod_contract.py::test_eod_workflow_run_workpage_uses_latest_draft_after_submit` still fails because `src/onetruth/application/services/dispatch_reporting_workbook.py` calls `zip()` with keyword arguments. This task records that caveat; it does not fix it.

## Objective
Freeze the stage-linked workpage action contract, the first supported logistics-family surface matrix, and the subject-link semantics for create/submit flows.

## Non-goals
- No backend route implementation.
- No frontend CTA rendering.
- No schedule write-path widening.
- No EOD finalization or approval-finalization changes.
- No new route family, shell, or workspace rewrite.

## Source files changed
- `codex/tasks/TASK-0146-stage-linked-workpage-action-contract-supported-surface-matrix-and-subject-link-semantics.md`
- `docs/planning/epics/EPIC-124.md`
- `codex/context/EPIC-124.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_BRIEF.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Source files to read first
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_BRIEF.md`
- `docs/planning/epics/EPIC-124.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/pages/RunWorkspacePage.tsx`

## Generated / downstream artifacts impacted
- frozen `workpage_actions[]` contract language for backend/frontend implementation
- frozen supported-surface matrix for the first logistics-family stage-linked CTA layer
- frozen relation-kind semantics for workpage-linked `draft` versus `response` artifacts

## Plan
1. Freeze the additive `workpage_actions[]` contract on workspace work items only.
2. Freeze the first supported logistics matrix for schedule and EOD workpage actions.
3. Freeze subject-link semantics for create/submit flows, including the rule that `draft` links do not satisfy requirements.
4. Synchronize repo-native epic/task/status memory so fresh sessions no longer treat EPIC-124 as a missing external package.

## Verification
- `python3 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-124|TASK-0146|workpage_actions|create_draft_then_open|submit_relation_kind|draft|response" docs/planning docs/status codex/tasks codex/context`

## Acceptance criteria
- The repo has one documented contract for stage-linked workpage actions.
- The supported logistics-family surfaces are explicit instead of implied.
- Relation-kind policy for `draft` versus `response` is explicit and frozen.
- The stop line is explicit: no route changes, no CTA rendering, no schedule Stage06/Stage07 widening, and no EOD finalization work.

## Outcome
- EPIC-124 is now repo-native instead of existing only in the external package.
- The repo now freezes `workpage_actions[]` as an additive workspace work-item projection, not a graph-node field, not a top-level action map, and not a second route family.
- The first supported-surface matrix is now explicit for `weekly_schedule_planning.v1` and `dispatch_reporting.v1` workspace work items.
- `draft` links are now explicitly non-satisfying for requirements, while `response` is the only workpage-linked relation kind reserved for future requirement satisfaction work.
- The known pre-existing EOD submit-path regression remains recorded as a baseline caveat for later reconciliation rather than being smuggled into this task.

## Commands run
- `python3 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-124|TASK-0146|workpage_actions|create_draft_then_open|submit_relation_kind|draft|response" docs/planning docs/status codex/tasks codex/context`

## Follow-ups
- `TASK-0147` should implement relation-kind-aware requirement counting, supported-surface enforcement, and write-boundary subject-link validation.
- `TASK-0148` should project `workpage_actions[]` onto supported workspace items and generate backend-owned workspace snapshots.
- `TASK-0149` should render the projected CTAs in the workspace UI and keep post-create/post-submit refresh truth synchronized.
- `TASK-0150` should close EPIC-124 and synchronize final docs/status/regression truth after behavior lands.
