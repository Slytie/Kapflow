---
id: TASK-0229
epic: EPIC-135
title: "Implement the post-publish live-dispatch replan adapter over base-seed plus delta truth"
status: TODO
owners: ["backend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0226", "TASK-0227"]
risk: high
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: []
---

## Why
After publish, sick/no-show and route-demand increases must stop riding the weekly-draft mutation path and move onto the already-selected live-dispatch authority model.

## Objective
Project post-publish repair and replan work through `live_dispatch.v1` while keeping the shared schedule popup as the operator surface.

## Non-goals
- generalized live-dispatch workpage productization
- live-dispatch agent runtime
- mutation of the published weekly base schedule

## Source files to read first
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/application/services/logistics_workpages_shared.py`
- `codex/tasks/TASK-0154-minimal-manual-daily-replan-lane-via-live-dispatch.md`

## Source files to change
- live-dispatch activation/replan orchestration helpers
- schedule popup contract/action builders
- sick/no-show and route-increase backend adapters
- backend tests for live-dispatch issue/replan truth

## Plan
1. Reuse the existing live-dispatch seed activation and official delta posture from `TASK-0154`.
2. Express post-publish sick/no-show and route-demand increases as issue-scoped live-dispatch replan work over:
   - immutable `dispatch.base_schedule_seed.workbook`
   - draft delta/replan truth
3. Keep official delta promotion separate from proposal review and apply/ignore actions.
4. Project the live-dispatch replan context back into the shared schedule popup so the operator does not need a separate day-of page to review the proposal.
5. Preserve the current direct weekly-draft sick/no-show action only as temporary compatibility fallback while the shared replan path lands.

## Verification
- live-dispatch runtime tests for post-publish sick/no-show and route-increase replan activation
- tests proving the published weekly base schedule stays immutable
- tests proving proposal/apply state flows through live-dispatch-backed context instead of weekly-draft mutation

## Acceptance criteria
- Post-publish sick/no-show and route-demand increases create or reuse issue-scoped live-dispatch replan truth.
- The shared popup can review post-publish live-dispatch proposals without widening weekly ownership.
- Base weekly seed truth remains immutable.
