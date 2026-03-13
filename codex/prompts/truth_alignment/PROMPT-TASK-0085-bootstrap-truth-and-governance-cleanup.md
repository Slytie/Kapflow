# Prompt for TASK-0085 — Bootstrap truth, CI honesty, and governance cleanup

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Make the repo’s day-to-day development posture truthful: real lint, real bootstrap/doctor checks, explicit runtime versions, CODEOWNERS validation, and a license.

## Prerequisites
- Depends on TASK-0075. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[repo\ claim = executable\ check\]

## Non-negotiable constraints
- `make lint` must mean what it says after this task.
- There must be one obvious bootstrap/doctor path for humans and Codex.
- Governance basics (`CODEOWNERS`, `LICENSE`, runtime version expectations) become explicit and testable.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0085`: **Bootstrap truth, CI honesty, and governance cleanup**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0085-bootstrap-truth-and-governance-cleanup.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `Makefile`
- `.github/workflows/main.yml`
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `.github/CODEOWNERS`
- `frontend/package.json`
- `README.md`

### What to figure out before coding
- Audit which repo claims are currently softer than they sound (`make lint`, bootstrap, versions, CODEOWNERS, licensing).
- Choose the lightest-weight bootstrap/doctor path that gives fresh Codex sessions and humans one reliable readiness check.
- Plan a CODEOWNERS path-validation test and explicit Node/runtime version declarations.

### Red-team checks
- Do not build a heavyweight internal developer platform just to add honest lint/bootstrap checks.
- Do not rename targets without making behavior truthful.
- Keep bootstrap checks deterministic and cheap enough to run in fresh Codex sessions.

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

Use this section only **after** the Ask-mode plan for `TASK-0085` has been reviewed and approved.

You are resuming `TASK-0085` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0085-bootstrap-truth-and-governance-cleanup.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `Makefile`
- `.github/workflows/main.yml`
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `.github/CODEOWNERS`
- `frontend/package.json`
- `README.md`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `Makefile`
- `.github/workflows/main.yml`
- `.github/CODEOWNERS`
- `frontend/package.json`
- `.nvmrc` (new)
- `scripts/bootstrap_dev.sh` or `scripts/doctor.py` (new)
- `LICENSE` (new)
- `tests/contract/test_codeowners_paths.py` (new)
- `README.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0085-bootstrap-truth-and-governance-cleanup.md`

### Verification to run
- `make lint`
- `make ci`
- `pytest tests/contract/test_codeowners_paths.py -q`
- `./scripts/bootstrap_dev.sh --check` or equivalent

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
