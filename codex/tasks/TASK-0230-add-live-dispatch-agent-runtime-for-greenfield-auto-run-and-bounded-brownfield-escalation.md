---
id: TASK-0230
epic: EPIC-135
title: "Add the live-dispatch agent runtime for greenfield auto-run and bounded brownfield escalation"
status: TODO
owners: ["backend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0229"]
risk: high
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: []
---

## Why
The weekly Stage04 agent runtime exists today, but post-publish live-dispatch replanning does not yet have an equivalent bounded agent/runtime path. EPIC-135 needs that explicit runtime rather than pretending the weekly agent can own day-of repair forever.

## Objective
Add a live-dispatch OpenAI agent runtime that mirrors the weekly runtime’s canonical execution evidence model and supports greenfield auto-run plus bounded brownfield escalation after publish.

## Non-goals
- a second execution/evidence system
- direct official-delta promotion by the agent
- replacing deterministic ranking for brownfield by default

## Source files to read first
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `src/onetruth/application/read_commands/runtime_views.py`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`

## Source files to change
- live-dispatch agent/runtime service modules
- API route specs and handlers for the new runtime entrypoint
- runtime tests and inspection-packet/proof surfaces
- shared status-projection code if new live-dispatch phases are needed

## Plan
1. Add a bounded live-dispatch agent runtime entrypoint analogous to the weekly Stage04 runtime, for example:
   - `POST /api/v1/human-tasks/{human_task_id}/live-dispatch-openai-agent`
2. Restrict the runtime to live-dispatch replan task kinds created by `TASK-0229`.
3. Emit the same class of canonical evidence as the weekly runtime:
   - task/execution policy truth
   - tool executions
   - proposal artifacts / runtime evidence
4. Auto-run the agent for greenfield post-publish `0 -> N` activation.
5. Keep brownfield escalation bounded and opt-in unless deterministic repair is insufficient.

## Verification
- runtime API tests for the new live-dispatch agent entrypoint
- scenario tests proving canonical execution evidence is emitted
- tests proving greenfield auto-run and brownfield escalation rules hold

## Acceptance criteria
- Post-publish greenfield activation can auto-run a live-dispatch agent through canonical runtime objects.
- Brownfield escalations use the same execution evidence model as weekly Stage04.
- No second or popup-local execution system is introduced.
