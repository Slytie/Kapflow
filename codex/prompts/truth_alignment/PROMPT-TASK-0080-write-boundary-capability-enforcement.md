# Prompt for TASK-0080 — Enforce capability decisions at the write boundary

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Enforce the frozen capability decisions at the write boundary so actions rejected by projections are also rejected by mutations, with no side effects on denial.

## Prerequisites
- Depends on TASK-0079. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[available\_actions(S,p) = allowed\_writes(S,p)\]

## Non-negotiable constraints
- Denied writes must leave no canonical row changes and append no authoritative events.
- The read side and write side must now speak the same capability vocabulary.
- No hotspot extraction in this task.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0080`: **Enforce capability decisions at the write boundary**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0080-write-boundary-capability-enforcement.md
- docs/planning/epics/EPIC-060.md
- codex/context/EPIC-060.md
- codex/context/EPIC-050.md
- codex/context/EPIC-030.md
- codex/context/EPIC-010.md
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-005.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/api/errors.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_workspace_actionability.py`

### What to figure out before coding
- Identify every mutation path that must consume shared capability decisions: claim/complete/review, approval respond, flag transition, artifact upload/attach.
- Choose the smallest explicit error-category change needed so forbidden/conflict outcomes are surfaced honestly.
- Plan tests that prove denied actions append no events and leave current-state rows unchanged.

### Red-team checks
- Do not change semantics that TASK-0077 froze.
- Do not rely on vague error-string heuristics if a local structured category can be introduced cleanly.
- If collaboration/upload is intentionally broader than claim/act, make that obvious in tests and docs rather than flattening everything into one permission.

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

Use this section only **after** the Ask-mode plan for `TASK-0080` has been reviewed and approved.

You are resuming `TASK-0080` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0080-write-boundary-capability-enforcement.md
- docs/planning/epics/EPIC-060.md
- codex/context/EPIC-060.md
- codex/context/EPIC-050.md
- codex/context/EPIC-030.md
- codex/context/EPIC-010.md
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/api/errors.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_workspace_actionability.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/errors.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_flag_transition_via_api.py` (new if missing)
- `tests/runtime/api/test_artifact_upload_profiles.py`
- `tests/security/test_write_path_capability_enforcement.py` (new)
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/tasks/TASK-0080-write-boundary-capability-enforcement.md`

### Verification to run
- `PYTHONPATH=src pytest tests/runtime/api/test_human_task_claim_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_approval_respond_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_flag_transition_via_api.py -q`
- `PYTHONPATH=src pytest tests/security/test_write_path_capability_enforcement.py -q`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
