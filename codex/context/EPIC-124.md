# EPIC-124 Context Pack - Stage-linked workpages and requirement-aware artifact linkage

Purpose:
- You are reviewing or extending the completed EPIC-124 workpage slice after EPIC-123.
- You need to preserve the supported stage-linked workspace workpage surface without creating a second truth path.
- You need to keep requirement satisfaction honest so workpage drafts never count as responses.

## Non-negotiable invariants to keep in mind
- Workpages remain derived surfaces; runtime rows, events, and artifacts remain canonical truth.
- Keep the current canonical route families intact:
  - run-backed workpages under `/runs/:workflowRunId/workpages/*`
  - artifact-backed EOD and schedule artifact routes under `/runs/:workflowRunId/workpages/*/artifacts/:artifactVersionId`
- Do not deepen EOD into final-packet or approval-finalization semantics in this epic.
- Do not broaden schedule beyond the current Stage04 `planning.draft_weekly_schedule.workbook` artifact lane.
- Draft links must not satisfy required uploads.
- Submitted response artifacts may satisfy supported requirements only when relation-kind policy says they should.
- Keep approval-review access distinct from approval response/finalization.
- Update repo-native docs, status, and task memory in the same change set whenever stage-linked action truth changes.

## Contracts and docs to treat as authoritative
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_BRIEF.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/epics/EPIC-124.md`
- `codex/context/EPIC-124.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/routes/workpages.py`
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/pages/RunWorkspacePage.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`

## TASK-0146 freeze
- `TASK-0146` is complete and doc-only.
- The additive contract seam is `workpage_actions[]` on workspace work items (`user_work[]` and `blocking_work[]`) only.
- Graph nodes do not gain workpage action metadata.
- The first supported surfaces are bounded to selected logistics-family workspace task/approval items only.
- `draft` is reserved for in-progress workpage association and never satisfies requirements.
- `response` is reserved for submitted workpage artifacts and is the only workpage-linked relation kind that later tasks may allow to satisfy supported requirements.
- No backend behavior or frontend CTA rendering changed in `TASK-0146`.

## Current repo status
- EPIC-122 is complete: canonical run-backed schedule and EOD workpage routes are live.
- EPIC-123 is complete: artifact-backed EOD and bounded Stage04 schedule artifact lanes are live.
- EPIC-124 is complete: the repo-native contract freeze, backend requirement/link semantics, backend workspace action projection/snapshots, and frontend CTA integration are all landed.
- Supported `/runs/:workflowRunId/workspace` items now expose and render backend-projected `workpage_actions[]`; graph nodes and unsupported queues remain action-free.
- `task_requirements.py` now applies the first relation-kind-aware workpage-safe satisfaction rule, and supported workpage create/submit flows now translate one optional `subject_link` into the existing artifact `links[]` seam.
- The targeted frontend runner note now remains explicit: use `npm --prefix frontend run test:run -- --fileParallelism=false ...` until the shared MSW artifact-map harness is parallel-safe.
- A known pre-existing baseline caveat remains: targeted workpage verification still fails the run-backed EOD latest-draft-after-submit path because `dispatch_reporting_workbook.py` calls `zip()` with keyword arguments.

## Completed implementation order inside this epic
1. `TASK-0146` - Freeze contract and semantics
2. `TASK-0147` - Backend requirement/link semantics
3. `TASK-0148` - Backend workspace/stage-linked action projection and snapshots
4. `TASK-0149` - Frontend CTA integration
5. `TASK-0150` - Closeout and doc/regression sync

## Post-epic posture
- EPIC-124 does not authorize schedule Stage06 publish editing, Stage07 seed/live-dispatch widening, EOD finalization, or a broader workspace rollout.
- The next app-facing epic remains intentionally unselected after closeout.

## Smallest context set for the next tasks
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_BRIEF.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/pages/RunWorkspacePage.tsx`

## Red-team questions for future runs
- Are we letting `draft`-linked artifacts satisfy a task requirement?
- Are we broadening into final-packet, Stage06 publish, Stage07 seed, or live-dispatch control semantics?
- Are we using frontend inference instead of backend-projected action metadata?
- Are we turning approval-review access into implicit approval-finalization behavior?
