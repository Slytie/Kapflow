# EPIC-124 - Stage-linked workpages and requirement-aware artifact linkage

## Summary
Build the next workpage layer so the repo can promote workpages from run/artifact routes into workflow-stage actions.

This epic is intentionally bounded:
- expose truthful workpage actions on supported logistics workspace task/approval surfaces
- preserve the current canonical run-backed and artifact-backed route families
- make task-linked workpage artifact flows relation-kind-aware so drafts do not satisfy requirements and submitted responses can

This epic is intentionally not EOD finalization, not Stage06/Stage07 schedule widening, and not a broad workspace modernization epic.

## Status
Complete on 2026-03-27. `TASK-0146` through `TASK-0150` are complete and together freeze the contract boundary, land the supported backend/frontend slice, and synchronize repo-native closeout memory.

Known baseline caveat: targeted workpage verification still exposes a pre-existing EOD submit-path failure in `tests/runtime/api/test_workpages_run_eod_contract.py::test_eod_workflow_run_workpage_uses_latest_draft_after_submit`, traced to `src/onetruth/application/services/dispatch_reporting_workbook.py`. Reconcile that baseline separately rather than broadening this epic.

## Scope
### In scope
- repo-native stage-linked workpage brief/plan and context pack
- workpage action contract freeze for supported logistics surfaces
- relation-kind-aware requirement satisfaction for workpage-linked drafts versus responses
- backend workpage create/submit subject-link support where needed
- backend projection of workpage actions on supported workspace task/approval surfaces
- frontend CTA/handoff integration for those projected actions
- closeout docs/status/context synchronization

### Out of scope
- EOD final-packet, approval finalization, or pointer-promotion work
- schedule Stage06 publish editing or Stage07 seed/live-dispatch editing
- schedule JSON-to-XLSX fidelity convergence
- generic spreadsheet-editor/runtime scope
- broad workspace redesign outside the supported logistics workpage actions

## Dependencies
- EPIC-122 (canonical run-backed workpage access)
- EPIC-123 (bounded Stage04 schedule artifact-backed lane)
- EPIC-050 (human-task queue / workspace surfaces)
- EPIC-060 (approval surfaces)
- EPIC-030 (artifact linkage / lineage remain canonical)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-124.md`

## Current repo status / rationale
- The repo already has canonical run-backed workpage routes for schedule and EOD.
- The repo already has artifact-backed EOD editing and bounded Stage04 schedule artifact-backed editing.
- `/demo/logistics` exposes the canonical run-backed workpage routes as the primary discoverable path.
- `task_requirements.py` now distinguishes workpage `draft` versus submitted `response` semantics for the first supported requirement-aware schedule surface.
- Canonical workpage create/submit flows now accept one optional `subject_link` object on supported surfaces only and derive relation kinds server-side.
- `/runs/:workflowRunId/workspace` now projects and renders additive `workpage_actions[]` on the supported logistics task/approval surfaces only; graph nodes, other queues, and drawer/detail surfaces remain out of scope.
- Backend-owned frontend contract fixtures now include the bounded workspace-action snapshots used by the EPIC-124 CTA layer.
- The next app-facing tranche remains intentionally unselected after EPIC-124 closeout; this epic does not imply Stage06/Stage07 widening, EOD finalization, or broader workspace rollout.

## Tasks
- TASK-0146 - DONE
- TASK-0147 - DONE
- TASK-0148 - DONE
- TASK-0149 - DONE
- TASK-0150 - DONE

## Red-team question
Are we still making existing logistics workpages usable from the real stage/task/approval surfaces of the workflow system, or are we quietly broadening into finalization, Stage06/Stage07 schedule expansion, or a full workspace rewrite before the workpage-action layer is actually implemented?
