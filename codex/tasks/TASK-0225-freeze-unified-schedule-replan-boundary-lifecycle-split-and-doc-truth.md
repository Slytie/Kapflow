---
id: TASK-0225
epic: EPIC-135
title: "Freeze the unified schedule replan boundary, lifecycle split, prerequisite truth, and repo memory"
status: TODO
owners: ["architect"]
reviewers: ["pm", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: ["docs-as-truth"]
---

## Why
The next tranche crosses weekly planning, live dispatch, workpages, and agent-runtime seams. We need one repo-native freeze of the architecture before implementation starts so later tasks do not reopen ownership questions or silently bypass canonical prerequisites.

## Scope
- add the long-form unified replan plan doc
- add EPIC-135 plus both context packs
- add the full TASK-0225..TASK-0232 stack to repo-native backlog truth
- add one ADR covering mirrored weekly/live contact inputs and the authored live-dispatch runtime surface requirement
- update active status/index memory to point fresh sessions at EPIC-135
- update weekly/live workflow-pack docs so the shared popup entry surface, mirrored contact inputs, and runtime-surface guardrails are described without blurring workflow ownership
- record that removing the visible scheduler task does not remove canonical task/execution/input truth and is only allowed after the current route-demand refresh-task path is replaced

## Out of scope
- runtime or frontend code changes
- contact-data authoring
- live-dispatch agent implementation
- popup redesign work

## Source files to read first
- `docs/planning/LOGISTICS_WORKPAGES_UNIFIED_REPLAN_AND_DYNAMIC_SCHEDULING_PLAN.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/weekly_schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/live_dispatch/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workpage_command_support.py`
- `src/onetruth/application/handlers/workpage_schedule_commands.py`

## Source files to change
- planning docs under `docs/planning/`
- epic/context/task memory under `docs/planning/epics/`, `codex/context/`, and `codex/tasks/`
- repo status/index memory under `docs/status/`, `docs/planning/EPICS.md`, and `docs/planning/TASK_INDEX.md`
- weekly/live workflow-pack docs
- ADR under `docs/architecture/`

## Plan
1. Freeze the lifecycle split: weekly before publish, live dispatch after publish, shared popup surface throughout.
2. Freeze the trigger rules: deterministic first, greenfield in-scope `0 -> N` auto-runs the scheduler agent, brownfield escalates only when needed.
3. Freeze prerequisite truth: Stage04 inputs plus existing requirement/actionability truth remain canonical gates even after the manual scheduler CTA is removed.
4. Freeze one additional repo rule: no new dataset keys or new runtime surfaces without authored workflow-pack updates.
5. Freeze the CTA-retirement guard: the old scheduler CTA may only be removed after the current route-demand refresh-task path is replaced.
6. Add the epic, context packs, task briefs, ADR, workflow-pack doc updates, and repo-memory updates in one coherent tranche.

## Verification
- `rg -n "EPIC-135|TASK-0225|shared popup|pre-publish|post-publish|driver_contact_directory|route-demand refresh|0 -> N|live-dispatch runtime" docs/planning docs/status docs/workflows docs/architecture codex/context codex/tasks`
- `git diff --check`

## Acceptance criteria
- EPIC-135 exists as the selected next app-facing workpage epic.
- The repo contains one long-form plan doc, one epic file, two context packs, one ADR, and eight task briefs for the tranche.
- `CURRENT_FOCUS`, `DECISIONS_SINCE_LAST`, `EPICS.md`, and `TASK_INDEX.md` point fresh sessions at EPIC-135.
- Weekly/live workflow-pack docs now describe the shared operator surface, mirrored contact inputs, and runtime-surface boundaries without widening workflow ownership.
