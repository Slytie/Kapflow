# Prompt for TASK-0084 — Make bundle kinds explicit and validate the exported payload

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Separate handoff, release, and runtime-workspace bundles explicitly, and validate the actual exported payload rather than only the tracked tree.

## Prerequisites
- Depends on TASK-0075. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[B_{validated} = B_{exported} = B_{released}\]

## Non-negotiable constraints
- Bundle kinds and trust assumptions must be explicit.
- Validation must be able to inspect the actual archive payload.
- Handoff bundles remain available, but they are not mislabeled as release artifacts.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0084`: **Make bundle kinds explicit and validate the exported payload**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0084-explicit-bundle-kinds-and-export-payload-validation.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `scripts/export_clean_source_bundle.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `docs/planning/REPO_HYGIENE.md`
- `README.md`

### What to figure out before coding
- Define explicit semantics and manifests for `handoff_source_bundle`, `release_source_bundle`, and `runtime_workspace_bundle`.
- Decide how validation should inspect the actual archive payload for each bundle kind.
- Plan how release bundles become provenance-oriented without breaking the existing handoff workflow.

### Red-team checks
- Do not confuse a handoff bundle with a release/provenance artifact.
- Do not keep validation scoped only to tracked files if export can include untracked source.
- Do not try to solve full SBOM/provenance in this task.

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

Use this section only **after** the Ask-mode plan for `TASK-0084` has been reviewed and approved.

You are resuming `TASK-0084` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0084-explicit-bundle-kinds-and-export-payload-validation.md
- docs/planning/epics/EPIC-080.md
- codex/context/EPIC-080.md
- `scripts/export_clean_source_bundle.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `docs/planning/REPO_HYGIENE.md`
- `README.md`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `scripts/export_clean_source_bundle.py`
- `scripts/validate_repo.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/contract/test_release_source_bundle_export.py` (new)
- `README.md`
- `docs/planning/REPO_HYGIENE.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0084-explicit-bundle-kinds-and-export-payload-validation.md`

### Verification to run
- `pytest tests/contract/test_clean_source_bundle_export.py -q`
- `pytest tests/contract/test_release_source_bundle_export.py -q`
- `python3 scripts/validate_repo.py`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
