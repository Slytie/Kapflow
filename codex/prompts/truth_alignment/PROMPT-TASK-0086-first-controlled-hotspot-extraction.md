# Prompt for TASK-0086 — First controlled hotspot extraction after invariants are stable

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Only after invariants are stable, perform the first controlled extraction from `workflow_task_lifecycle.py` behind compatibility seams and characterization tests.

## Prerequisites
- Depends on TASK-0080. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0081. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0082. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0083. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[J(m) \approx \lambda_{change}(m)\cdot B(m)\cdot P_{break}(m)\cdot T_{debug}(m)\]

## Non-negotiable constraints
- One bounded flow family only in the first extraction.
- Compatibility re-exports are preferred over immediate import churn.
- Behavior must stay frozen by earlier invariant tasks and characterization tests.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0086`: **First controlled hotspot extraction after invariants are stable**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0086-first-controlled-hotspot-extraction.md
- docs/planning/epics/EPIC-040.md
- codex/context/EPIC-040.md
- codex/context/EPIC-060.md
- codex/context/EPIC-030.md
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-003.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `tests/runtime/api/*`
- `tests/security/*`
- `tests/unit/*`

### What to figure out before coding
- Choose the first extraction target by risk and cohesion, not by raw LOC: artifact ingress, approval response, flag transitions, or task claim/complete.
- Identify any missing characterization tests before moving code.
- Plan compatibility re-exports so callers do not churn while the seam stabilizes.

### Red-team checks
- Do not start here unless TASK-0080 through TASK-0083 are complete and green.
- Do not split the hotspot into smaller files while preserving unresolved contradictions.
- Do not introduce import cycles or flag-day path churn.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- Which bounded flow family you will extract first, and why it has the best risk/cohesion tradeoff.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0086` has been reviewed and approved.

You are resuming `TASK-0086` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0086-first-controlled-hotspot-extraction.md
- docs/planning/epics/EPIC-040.md
- codex/context/EPIC-040.md
- codex/context/EPIC-060.md
- codex/context/EPIC-030.md
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `tests/runtime/api/*`
- `tests/security/*`
- `tests/unit/*`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- new handler modules under `src/onetruth/application/handlers/`
- relevant tests where imports or characterization harnesses need updating
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/tasks/TASK-0086-first-controlled-hotspot-extraction.md`

### Verification to run
- Targeted pytest slices for every moved command family
- `python3 scripts/validate_repo.py --schemas-only`
- import-cycle check if/when a repo-native check exists

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
