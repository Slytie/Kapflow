# Unified replan architecture findings - 2026-04-25

## Purpose
Record the repo-grounded findings that led to EPIC-135 selection and the lifecycle-split architecture.

## Findings

### 1. The current quick-edit posture is centralized in the shell
`frontend/src/app/AppShell.tsx` already provides:
- shared top chrome
- shared quick-edit modal entrypoints
- route-safe workpage context

That means the next tranche should extend the existing popup shell instead of adding a parallel operator surface.

### 2. The current schedule popup is still a weekly draft editor
`frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx` currently owns:
- preview recalculation
- save draft
- direct Sick / No Show mutation
- artifact refresh/reopen behavior

This is the main reason the current popup cannot simply absorb post-publish day-of control unchanged.

### 3. The existing Sick / No Show backend path is weekly-truth preserving but lifecycle-limited
`src/onetruth/application/handlers/workpage_schedule_commands.py` creates:
- an approved availability exception
- a repinned weekly dependency manifest
- a superseding weekly draft

That is valid for the current pre-publish bounded surface but not the right long-term owner for post-publish day-of repair.

### 4. Route-demand auto-rescheduling does not exist yet
`route-demand-v0` currently:
- saves immutable route-demand truth
- marks schedule drift / refresh follow-up
- does not auto-run scheduling

Moving from “refresh follow-up” to “dynamic greenfield activation” is therefore a real architecture change, not a UI wiring tweak.

### 5. The weekly scheduler agent is tied to Stage04 human-task truth
The existing agent runtime:
- runs only through the weekly Stage04 human-task endpoint
- depends on canonical input bindings
- emits canonical execution/policy evidence

This confirms that pre-publish automation should reuse that path rather than inventing a popup-local scheduler command.

### 6. Pre-publish and post-publish cannot be owned by the same backend lane
Weekly planning owns pre-publish draft/build truth.
Live dispatch owns post-publish issue/delta truth.
Live dispatch also requires published base-seed materialization.

Therefore the clean design is hybrid by lifecycle state, not one backend for every case.

### 7. Deterministic candidate infrastructure already exists
The repo already contains:
- hard-filter candidate generation
- deterministic scoring
- workpage checks and driver metrics

This supports the “deterministic first, agent second” design and avoids making every repair an agent-only operation.

### 8. Driver phone numbers are missing from canonical truth
No current scheduling artifact/projection contains contact data.
Adding phone numbers therefore requires a new authority/artifact family rather than a frontend-only embellishment.

### 9. Runtime status can be made canonical without a new system
The repo already has:
- `task_run`
- `human_task`
- `execution_session`
- `tool_execution`
- existing timeline/subgraph patterns on task/detail surfaces

The popup should project those objects rather than inventing a separate status model.

## Consequences for EPIC-135
- one shared `Edit Weekly Schedule` popup surface
- weekly-backed behavior before publish
- live-dispatch-backed behavior after publish
- deterministic ranking first
- greenfield `0 -> N` auto-agent trigger
- separate contact authority
- canonical runtime-backed status
