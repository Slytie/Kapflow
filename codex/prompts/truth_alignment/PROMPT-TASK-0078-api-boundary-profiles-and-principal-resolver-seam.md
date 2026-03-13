# Prompt for TASK-0078 — Add explicit API boundary profiles and a principal-resolver seam

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Make the API trust model explicit by adding boundary profiles and a principal-resolver seam, so trusted headers remain a deliberate local/CI mode instead of an ambient default.

## Prerequisites
- Depends on TASK-0077. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[I_{asserted} \neq I_{attested}\]

## Non-negotiable constraints
- Trusted request headers are legal only in `local_dev` and `ci_test`.
- `shared_env` must fail closed if no non-header principal adapter is configured.
- No capability-enforcement changes land here yet.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0078`: **Add explicit API boundary profiles and a principal-resolver seam**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0078-api-boundary-profiles-and-principal-resolver-seam.md
- docs/planning/epics/EPIC-010.md
- codex/context/EPIC-010.md
- `docs/patterns/cards/PATTERN-008.md`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

### What to figure out before coding
- Design the minimal profile model for `local_dev`, `ci_test`, and `shared_env`.
- Define the `PrincipalResolver` seam so shared-env can fail closed without requiring JWT/OIDC work in this task.
- Spell out which CORS/body-handling behavior is local-dev-only versus allowed in shared environments.

### Red-team checks
- Assume a malicious webpage can reach a developer’s localhost server; reflective CORS plus trusted headers is a real risk.
- Do not leave trusted-header resolution as an implicit default if profile config is absent.
- Do not broaden this into a full API-shell rewrite.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- The boundary/profile split you are going to encode and the trust assumptions on each side.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0078` has been reviewed and approved.

You are resuming `TASK-0078` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0078-api-boundary-profiles-and-principal-resolver-seam.md
- docs/planning/epics/EPIC-010.md
- codex/context/EPIC-010.md
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `tests/runtime/api/test_request_context_profiles.py` (new)
- `README.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-010.md`
- `codex/context/EPIC-010.md`
- `codex/tasks/TASK-0078-api-boundary-profiles-and-principal-resolver-seam.md`

### Verification to run
- `PYTHONPATH=src pytest tests/runtime/api/test_request_context_profiles.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_cross_scope_api_denial.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
