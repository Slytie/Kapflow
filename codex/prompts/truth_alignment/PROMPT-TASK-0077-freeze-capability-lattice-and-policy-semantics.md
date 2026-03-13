# Prompt for TASK-0077 — Freeze the capability lattice and policy semantics

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Freeze the capability lattice before hardening handlers so routing hints, claimability, executability, collaboration/upload rights, and overrides stop drifting semantically.

## Prerequisites
- Depends on TASK-0076. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[\Pi_{route},\; \Pi_{claim},\; \Pi_{act},\; \Pi_{collab},\; \Pi_{override}\]

## Non-negotiable constraints
- This task is semantics + docs + contract tests only.
- The result must be small and executable: one matrix, one contract test, one explicit vocabulary.
- Future tasks must be able to import these semantics without reinterpretation.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0077`: **Freeze the capability lattice and policy semantics**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md
- docs/planning/epics/EPIC-050.md
- codex/context/EPIC-050.md
- codex/context/EPIC-060.md
- codex/context/EPIC-090.md
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `schemas/policy/permissions.yaml`
- `src/onetruth/application/services/task_actionability.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`

### What to figure out before coding
- Map the current semantics of `candidate_roles`, `required_role`, current actionability projections, and current write-path tests.
- Produce one explicit matrix covering routing, claim, act, collaborate/upload, approval response, flag transition, and override/escalation.
- Identify every contradiction between docs, projections, and runtime tests; resolve them in docs/tests first, not in handlers.

### Red-team checks
- Do not smuggle handler changes or write-path enforcement into this task.
- Do not create a giant theory-only policy document with no executable tests-as-spec.
- If `candidate_roles` is not a hard permission, say so explicitly and define separate claim/override semantics.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- The explicit capability matrix you propose to freeze (routing / claim / act / collaborate / override).
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0077` has been reviewed and approved.

You are resuming `TASK-0077` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md
- docs/planning/epics/EPIC-050.md
- codex/context/EPIC-050.md
- codex/context/EPIC-060.md
- codex/context/EPIC-090.md
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `schemas/policy/permissions.yaml`
- `src/onetruth/application/services/task_actionability.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md` (only if authority assumptions materially change)
- `schemas/policy/permissions.yaml` (only if vocabulary gaps are closed here)
- `docs/planning/TEST_MATRIX.md`
- `tests/contract/test_capability_matrix.py` (new)
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-050.md`
- `codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md`

### Verification to run
- `pytest tests/contract/test_capability_matrix.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
