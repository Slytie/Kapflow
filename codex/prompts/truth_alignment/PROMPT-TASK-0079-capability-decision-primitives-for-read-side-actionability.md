# Prompt for TASK-0079 — Introduce capability-decision primitives for read-side actionability

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Introduce small shared capability-decision primitives on the read side so actionability is computed from one runtime vocabulary before write-path parity is enforced.

## Prerequisites
- Depends on TASK-0077. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0078. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[available\_actions(S,p) = project(decide(S,p))\]

## Non-negotiable constraints
- Read-side actionability must consume shared capability decisions.
- Per-aggregate modules should stay close to aggregate semantics.
- Reason codes should be structured, not magic booleans or stringly-typed guesses.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0079`: **Introduce capability-decision primitives for read-side actionability**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md
- docs/planning/epics/EPIC-060.md
- codex/context/EPIC-060.md
- codex/context/EPIC-050.md
- codex/context/EPIC-010.md
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-005.md`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `tests/runtime/api/test_workspace_actionability.py`

### What to figure out before coding
- Design a tiny common `Principal` and `CapabilityDecision` with structured reason codes.
- Split capability logic by aggregate (`tasks`, `approvals`, `flags`, `artifacts`) instead of building one cross-cutting authz module.
- Map existing actionability fields to these shared decisions while preserving the semantics frozen in TASK-0077.

### Red-team checks
- Do not let `capabilities/` become the next hotspot or a kitchen-sink authz package.
- Do not change write-path behavior in this task.
- Keep response shapes stable unless TASK-0077 explicitly changed semantics.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0079` has been reviewed and approved.

You are resuming `TASK-0079` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md
- docs/planning/epics/EPIC-060.md
- codex/context/EPIC-060.md
- codex/context/EPIC-050.md
- codex/context/EPIC-010.md
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `tests/runtime/api/test_workspace_actionability.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/services/capabilities/__init__.py` (new)
- `src/onetruth/application/services/capabilities/tasks.py` (new)
- `src/onetruth/application/services/capabilities/approvals.py` (new)
- `src/onetruth/application/services/capabilities/flags.py` (new)
- `src/onetruth/application/services/capabilities/artifacts.py` (new)
- `tests/unit/test_capability_decisions.py` (new)
- `tests/runtime/api/test_workspace_actionability.py`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md`

### Verification to run
- `pytest tests/unit/test_capability_decisions.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
