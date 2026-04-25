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
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/services/capabilities/tasks.py`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `src/onetruth/application/read_commands/runtime_views.py`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`

## Source files to change
- live-dispatch workflow-pack/runtime-surface docs
- capability/actionability docs or services for the specialized execute surface
- live-dispatch agent/runtime service modules
- API route specs and handlers for the new runtime entrypoint
- runtime tests and inspection-packet/proof surfaces
- shared status-projection code if new live-dispatch phases are needed

## Plan
1. First author the live-dispatch runtime surface in the workflow pack and capability/actionability layer before any endpoint is added.
2. Add a bounded live-dispatch agent runtime entrypoint analogous to the weekly Stage04 runtime, for example:
   - `POST /api/v1/human-tasks/{human_task_id}/live-dispatch-openai-agent`
3. Restrict the runtime to live-dispatch replan task kinds created by `TASK-0229`.
4. Emit the same class of canonical evidence as the weekly runtime:
   - task/execution policy truth
   - tool executions
   - proposal artifacts / runtime evidence
5. Auto-run the agent for greenfield post-publish `0 -> N` activation.
6. Keep brownfield escalation bounded and opt-in unless deterministic repair is insufficient.

## Verification
- workflow-pack/actionability tests or doc checks for the authored live runtime surface
- runtime API tests for the new live-dispatch agent entrypoint
- scenario tests proving canonical execution evidence is emitted
- tests proving greenfield auto-run and brownfield escalation rules hold

## Acceptance criteria
- The live-dispatch runtime/actionability surface is authored before the public runtime entrypoint exists.
- Post-publish greenfield activation can auto-run a live-dispatch agent through canonical runtime objects.
- Brownfield escalations use the same execution evidence model as weekly Stage04.
- No second or popup-local execution system is introduced.
