---
id: TASK-0228
epic: EPIC-135
title: "Implement the pre-publish weekly-backed replan adapter and in-scope greenfield trigger"
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
Before publish, the only truthful scheduler execution path is still the weekly Stage04 lane. We need to reuse that truth when route demand crosses `0 -> N` and when brownfield pre-publish repair is requested, without forcing operators back to a manual task click.

## Objective
Add a weekly-backed replan adapter that can create or reuse canonical weekly task/execution context and trigger greenfield scheduling automatically for in-scope `0 -> N` route additions before publish.

## Non-goals
- post-publish live-dispatch repair
- a new generic scheduler endpoint
- browser-driven task creation

## Source files to read first
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/services/schedule_control/stage04_input_registry.py`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/handlers/workpage_command_support.py`
- `src/onetruth/application/services/logistics_workpages_shared.py`
- `frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx`

## Source files to change
- weekly scheduling runtime/task orchestration helpers
- route-demand save/trigger logic
- schedule popup action/contract builders
- backend tests for trigger and prerequisite handling

## Plan
1. Detect route-demand transitions from `0 -> N` on service dates inside the active weekly planning scope during route-demand save.
2. Resolve or create the weekly-backed replan context using canonical Stage04 truth rather than popup-local state.
3. Reuse the existing weekly Stage04 human-task/agent runtime for greenfield activation:
   - create or reuse the bounded Stage04 work item context
   - preserve required-input gating
   - expose blocked runtime status when prerequisites are missing or task reuse is unsafe
4. Keep brownfield pre-publish changes deterministic-first:
   - generate proposal/candidate truth
   - do not auto-run the agent unless explicitly escalated later
5. Preserve the two-week route-demand horizon but suppress auto-triggering for out-of-scope future dates.

## Verification
- tests proving in-scope `0 -> N` route additions auto-trigger scheduling before publish
- tests proving missing Stage04 inputs block cleanly
- tests proving out-of-scope future dates still save route-demand truth without auto-opening replanning

## Acceptance criteria
- Pre-publish `0 -> N` route additions inside active scope create or reuse canonical weekly replan work and auto-start scheduling.
- Brownfield pre-publish changes stay deterministic-first.
- The old manual scheduler click is no longer required for the greenfield pre-publish path.
